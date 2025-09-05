//! blake-bench: Compare BLAKE2 vs BLAKE3 performance with throughput and latency modes.

// cargo build --release --features "b3rayon"
// target/release/blake-bench --markdown --include-parallel > result.md

#![cfg_attr(target_arch = "s390x", feature(stdarch_s390x_feature_detection))]

use clap::{ArgAction, Parser, ValueEnum};
use rand::{rngs::StdRng, RngCore, SeedableRng};
use std::fmt::Write as _;
use std::time::{Duration, Instant};
use sysinfo::System;

#[derive(ValueEnum, Clone, Copy, Debug)]
enum ImplKind {
    Blake3Single,
    #[cfg(feature = "b3rayon")]
    Blake3Parallel,
    Blake2b256,
    Blake2s256,
}

impl ImplKind {
    fn all(_include_parallel: bool) -> Vec<Self> {
        let mut _v = vec![Self::Blake3Single, Self::Blake2b256, Self::Blake2s256];
        #[cfg(feature = "b3rayon")]
        if _include_parallel {
            _v.insert(1, Self::Blake3Parallel);
        }
        _v
    }
    fn name(self) -> &'static str {
        match self {
            ImplKind::Blake3Single => "blake3_single",
            #[cfg(feature = "b3rayon")]
            ImplKind::Blake3Parallel => "blake3_parallel",
            ImplKind::Blake2b256 => "blake2b_256",
            ImplKind::Blake2s256 => "blake2s_256v1",
        }
    }
}

#[derive(ValueEnum, Clone, Copy, Debug)]
enum Pattern {
    Random,
    Zero,
    Repeat16,
}

impl Pattern {
    fn all() -> &'static [Pattern] {
        &[Pattern::Random, Pattern::Zero, Pattern::Repeat16]
    }
    fn name(self) -> &'static str {
        match self {
            Pattern::Random => "random",
            Pattern::Zero => "zero",
            Pattern::Repeat16 => "repeat16",
        }
    }
}

#[derive(Parser, Debug)]
#[command(
    name = "blake-bench",
    author,
    version,
    about = "BLAKE3 vs BLAKE2 micro/throughput benchmarks"
)]
struct Opts {
    #[arg(short = 'i', long = "impl", value_enum)]
    impls: Vec<ImplKind>,
    #[arg(short = 'p', long = "pattern", value_enum)]
    patterns: Vec<Pattern>,
    #[arg(short = 's', long = "size")]
    sizes: Vec<usize>,
    #[arg(long = "min-duration-ms", default_value_t = 600)]
    min_duration_ms: u64,
    #[arg(long = "trials", default_value_t = 5)]
    trials: u32,
    #[arg(long = "latency-threshold-bytes", default_value_t = 1024)]
    latency_threshold: usize,
    #[arg(long = "csv", action = ArgAction::SetTrue)]
    csv: bool,
    #[arg(long = "markdown", action = ArgAction::SetTrue)]
    markdown: bool,
    #[arg(long = "include-parallel", action = ArgAction::SetTrue)]
    include_parallel: bool,
    #[arg(long = "threads")]
    threads: Option<usize>,
}

fn main() {
    let mut opts = Opts::parse();
    if opts.impls.is_empty() {
        opts.impls = ImplKind::all(opts.include_parallel);
    }
    if opts.patterns.is_empty() {
        opts.patterns = Pattern::all().to_vec();
    }
    if opts.sizes.is_empty() {
        opts.sizes = vec![
            0,
            1,
            32,
            64,
            128,
            1024,
            4 * 1024,
            16 * 1024,
            64 * 1024,
            256 * 1024,
            1024 * 1024,
            8 * 1024 * 1024,
            64 * 1024 * 1024,
        ];
    }
    if let Some(_n) = opts.threads {
        #[cfg(feature = "b3rayon")]
        {
            if rayon::ThreadPoolBuilder::new()
                .num_threads(_n)
                .build_global()
                .is_err()
            {
                eprintln!("Warning: global Rayon pool already set; --threads ignored.");
            }
        }
    }

    let mut inputs = Vec::new();
    for &sz in &opts.sizes {
        for &pat in &opts.patterns {
            inputs.push((sz, pat, make_buf(sz, pat)));
        }
    }

    let min_window = Duration::from_millis(opts.min_duration_ms);
    let mut throughput_rows = Vec::new();
    let mut latency_rows = Vec::new();

    for &imp in &opts.impls {
        for (sz, pat, data) in &inputs {
            if *sz <= opts.latency_threshold {
                let med = median_ns(|| bench_latency(imp, data), opts.trials);
                latency_rows.push(LatencyRow {
                    impl_name: imp.name().to_string(),
                    size: *sz,
                    pattern: pat.name().to_string(),
                    ns_per_op: med as u128,
                });
            } else {
                let med = median_f64(|| bench_throughput(imp, data, min_window), opts.trials);
                throughput_rows.push(ThroughputRow {
                    impl_name: imp.name().to_string(),
                    size: *sz,
                    pattern: pat.name().to_string(),
                    mib_per_s: med,
                });
            }
        }
    }

    if opts.csv {
        print_csv(&throughput_rows, &latency_rows);
    } else if opts.markdown {
        print_markdown(&throughput_rows, &latency_rows);
    } else {
        print_tables(&throughput_rows, &latency_rows);
    }
}

fn hash_blake3_single(buf: &[u8]) -> [u8; 32] {
    blake3::hash(buf).into()
}
#[cfg(feature = "b3rayon")]
fn hash_blake3_parallel(buf: &[u8]) -> [u8; 32] {
    use blake3::Hasher;
    let mut h = Hasher::new();
    h.update_rayon(buf);
    h.finalize().into()
}
fn hash_blake2b_256(buf: &[u8]) -> [u8; 32] {
    use blake2::{digest::consts::U32, Blake2b, Digest};
    type Blake2b256 = Blake2b<U32>;
    let mut hasher = Blake2b256::new();
    hasher.update(buf);
    hasher.finalize().into()
}
fn hash_blake2s_256(buf: &[u8]) -> [u8; 32] {
    use blake2::{Blake2s256, Digest};
    let mut hasher = Blake2s256::new();
    hasher.update(buf);
    hasher.finalize().into()
}

fn digest_once(kind: ImplKind, buf: &[u8]) -> [u8; 32] {
    match kind {
        ImplKind::Blake3Single => hash_blake3_single(buf),
        #[cfg(feature = "b3rayon")]
        ImplKind::Blake3Parallel => hash_blake3_parallel(buf),
        ImplKind::Blake2b256 => hash_blake2b_256(buf),
        ImplKind::Blake2s256 => hash_blake2s_256(buf),
    }
}

fn make_buf(len: usize, pattern: Pattern) -> Vec<u8> {
    match pattern {
        Pattern::Zero => vec![0u8; len],
        Pattern::Repeat16 => {
            let base: [u8; 16] = *b"0123456789ABCDEF";
            (0..len).map(|i| base[i % 16]).collect()
        }
        Pattern::Random => {
            let mut v = vec![0u8; len];
            let mut rng = StdRng::seed_from_u64(0xDEADBEEF);
            rng.fill_bytes(&mut v);
            v
        }
    }
}

fn bench_latency(kind: ImplKind, data: &[u8]) -> u64 {
    let target_iters = if data.len() <= 64 {
        2_000_000u64
    } else {
        500_000u64
    };
    let mut _sink = [0u8; 32];
    for _ in 0..10_000 {
        _sink = digest_once(kind, data);
    }
    let start = Instant::now();
    for _ in 0..target_iters {
        _sink = digest_once(kind, data);
        std::hint::black_box(&_sink);
    }
    let elapsed = start.elapsed().as_nanos();
    (elapsed / target_iters as u128) as u64
}

fn bench_throughput(kind: ImplKind, data: &[u8], min_window: Duration) -> f64 {
    let mut total_bytes: u128 = 0;
    let mut _sink = [0u8; 32];
    let warmup_end = Instant::now() + Duration::from_millis(100);
    while Instant::now() < warmup_end {
        _sink = digest_once(kind, data);
        total_bytes += data.len() as u128;
        std::hint::black_box(&_sink);
    }
    total_bytes = 0;
    let start = Instant::now();
    while start.elapsed() < min_window {
        _sink = digest_once(kind, data);
        total_bytes += data.len() as u128;
        std::hint::black_box(&_sink);
    }
    let secs = start.elapsed().as_secs_f64();
    (total_bytes as f64 / (1024.0 * 1024.0)) / secs
}

fn median_ns<F: FnMut() -> u64>(mut f: F, trials: u32) -> u64 {
    let mut v: Vec<u64> = (0..trials).map(|_| f()).collect();
    v.sort_unstable();
    v[(v.len() - 1) / 2]
}
fn median_f64<F: FnMut() -> f64>(mut f: F, trials: u32) -> f64 {
    let mut v: Vec<f64> = (0..trials).map(|_| f()).collect();
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    v[(v.len() - 1) / 2]
}

#[derive(Debug, Clone)]
struct ThroughputRow {
    impl_name: String,
    size: usize,
    pattern: String,
    mib_per_s: f64,
}
#[derive(Debug, Clone)]
struct LatencyRow {
    impl_name: String,
    size: usize,
    pattern: String,
    ns_per_op: u128,
}

fn print_csv(throughput: &[ThroughputRow], latency: &[LatencyRow]) {
    println!("kind,size,pattern,metric,value");
    for r in throughput {
        println!(
            "{},{},{},mib_per_s,{:.3}",
            r.impl_name, r.size, r.pattern, r.mib_per_s
        );
    }
    for r in latency {
        println!(
            "{},{},{},ns_per_op,{}",
            r.impl_name, r.size, r.pattern, r.ns_per_op
        );
    }
}

fn print_tables(throughput: &[ThroughputRow], latency: &[LatencyRow]) {
    let mut out = String::new();
    let mut thr = throughput.to_vec();
    thr.sort_by_key(|r| (r.pattern.clone(), r.size, r.impl_name.clone()));
    let mut last_pat = String::new();
    for r in thr {
        if r.pattern != last_pat {
            if !last_pat.is_empty() {
                println!("{out}");
                out.clear();
            }
            last_pat = r.pattern.clone();
            writeln!(
                &mut out,
                "\n## Throughput (MiB/s) — pattern: {}\n",
                r.pattern
            )
            .unwrap();
            writeln!(
                &mut out,
                "| Impl | Size (B) | MiB/s |\n|------|---------:|------:|"
            )
            .unwrap();
        }
        writeln!(
            &mut out,
            "| {} | {} | {:.3} |",
            r.impl_name, r.size, r.mib_per_s
        )
        .unwrap();
    }
    if !out.is_empty() {
        println!("{out}");
        out.clear();
    }
    let mut lat = latency.to_vec();
    lat.sort_by_key(|r| (r.pattern.clone(), r.size, r.impl_name.clone()));
    let mut last_pat = String::new();
    for r in lat {
        if r.pattern != last_pat {
            if !last_pat.is_empty() {
                println!("{out}");
                out.clear();
            }
            last_pat = r.pattern.clone();
            writeln!(
                &mut out,
                "\n## Latency (ns/op) — tiny sizes, pattern: {}\n",
                r.pattern
            )
            .unwrap();
            writeln!(
                &mut out,
                "| Impl | Size (B) | ns/op |\n|------|---------:|-----:|"
            )
            .unwrap();
        }
        writeln!(
            &mut out,
            "| {} | {} | {} |",
            r.impl_name, r.size, r.ns_per_op
        )
        .unwrap();
    }
    if !out.is_empty() {
        println!("{out}");
    }
}

fn cpu_flags() -> String {
    use std::collections::HashSet;

    let mut set: HashSet<String> = HashSet::new();

    // ---- x86/x86_64 ----
    #[cfg(any(target_arch = "x86", target_arch = "x86_64"))]
    {
        if std::arch::is_x86_feature_detected!("sse2") {
            set.insert("sse2".to_string());
        }
        if std::arch::is_x86_feature_detected!("avx") {
            set.insert("avx".to_string());
        }
        if std::arch::is_x86_feature_detected!("avx2") {
            set.insert("avx2".to_string());
        }
    }

    // ---- aarch64 ----
    #[cfg(target_arch = "aarch64")]
    {
        if std::arch::is_aarch64_feature_detected!("neon") {
            set.insert("neon".to_string());
        }
    }

    // ---- s390x ----
    #[cfg(target_arch = "s390x")]
    {
        // Nightly gate at crate root:
        // #![feature(stdarch_s390x_feature_detection)]

        // Rust names: vx -> "vector", vxe -> "vector-enhancements-1", vxe2 -> "vector-enhancements-2"
        if std::arch::is_s390x_feature_detected!("vector") {
            set.insert("vx".to_string());
        }
        if std::arch::is_s390x_feature_detected!("vector-enhancements-1") {
            set.insert("vxe".to_string());
        }
        if std::arch::is_s390x_feature_detected!("vector-enhancements-2") {
            set.insert("vxe2".to_string());
        }

        #[cfg(target_os = "linux")]
        if let Ok(txt) = std::fs::read_to_string("/proc/cpuinfo") {
            for line in txt.lines() {
                if let Some(rest) = line.strip_prefix("features") {
                    if let Some(idx) = rest.find(':') {
                        for tok in rest[idx + 1..].split_whitespace() {
                            set.insert(tok.to_string()); // OWN the token (prevents E0597)
                        }
                    }
                }
            }
        }
    }

    if set.is_empty() {
        "unknown".to_string()
    } else {
        let mut v: Vec<_> = set.into_iter().collect();
        v.sort_unstable();
        v.join(", ")
    }
}

fn gather_metadata() -> String {
    let mut sys = System::new_all();
    sys.refresh_all();
    let cpu_brand = sys
        .cpus()
        .first()
        .map(|c| c.brand().to_string())
        .unwrap_or_default();
    let cpu_cores = num_cpus::get_physical();
    let cpu_threads = num_cpus::get();
    let total_mem_gb = sys.total_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let os_name = sysinfo::System::name().unwrap_or_default();
    let os_version = sysinfo::System::os_version().unwrap_or_default();
    let kernel = sysinfo::System::kernel_version().unwrap_or_default();
    let rustc_ver = rustc_version_runtime::version().to_string();
    format!("**Host:** {}  \n**Cores/Threads:** {}/{}  \n**Memory:** {:.1} GiB  \n**OS:** {} {} (kernel {})  \n**Compiler:** rustc {}  \n**Build:** portable | target-cpu=native  \n**CPU flags:** {}  \n\n", cpu_brand, cpu_cores, cpu_threads, total_mem_gb, os_name, os_version, kernel, rustc_ver, cpu_flags())
}

fn print_markdown(throughput: &[ThroughputRow], latency: &[LatencyRow]) {
    println!("# Hash Benchmarks (BLAKE3 vs BLAKE2)\n");
    print!("{}", gather_metadata());
    print_tables(throughput, latency);
    println!("\n## Conclusion\n- Summarize whether BLAKE3 ≥ BLAKE2 across sizes & platforms.\n- Call out any exceptions.\n");
}
