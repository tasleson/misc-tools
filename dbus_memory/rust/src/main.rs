extern crate dbus;

// Test dbus service in rust to get an idea of memory footprint.

use dbus::{Connection, BusType, NameFlag};
use dbus::tree::{Factory, DataType};
use std::sync::Arc;

#[derive(Debug, Default)]
struct OPData;

impl DataType for OPData {
    type Tree = ();
    type ObjectPath = String;
    type Property = ();
    type Interface = ();
    type Method = ();
    type Signal = ();
}

fn main() {
    let c = Connection::get_private(BusType::Session).unwrap();
    c.register_name("com.blah.storage", NameFlag::ReplaceExisting as u32).unwrap();

    let f = Factory::new_fn::<OPData>();
    let mut tree = f.tree(());

    tree = tree.add(f.object_path("/com/blah/storage/block", "".to_owned())
        .introspectable()
        .object_manager()
        .add(
        f.interface("com.blah.storage.Manager", ()).add_m(
            f.method("Version", (), |m| {
                let s = "0.0.1";
                Ok(vec!(m.msg.method_return().append1(s)))
            }).outarg::<&str,_>("reply")
        )
    ));

    let mut interface = f.interface("com.blah.storage.BlockDevice", ())
        .add_m(f.method("Hello", (), |m| {
                let s = format!("Hello {}!", m.msg.sender().unwrap());
                Ok(vec!(m.msg.method_return().append1(s)))
                }).outarg::<&str,_>("reply")
        );

    interface = interface.add_p(f.property::<&str,_>("Name", ())
        .on_get(|i,p| { i.append(p.path.get_data()); Ok(()) }));
    interface = interface.add_p(f.property::<&str,_>("uuid", ())
        .on_get(|i,_| { i.append("kQ1BLF-iBTn-FiHR-x8yI-DEqt-Kyd4-JfbadZ"); Ok(()) }));
    interface = interface.add_p(f.property::<u32,_>("some_count", ())
        .on_get(|i,_| { i.append(0u32); Ok(()) }));

    for some_u64 in 0..5 {
        let n = format!("u64_{}", some_u64);
        interface = interface.add_p(f.property::<u64,_>(n, ()).on_get(|i,_| { i.append(0u64); Ok(()) }));
    }

    for some_strings in 0..7 {
        let name = format!("string_d_{}", some_strings);
        let value = format!("some bogus data {}", some_strings);
        interface = interface.add_p(f.property::<&str,_>(name, ()).on_get(move |i,_| { i.append(&value); Ok(()) }));
    }

    for some_bools in 0..5 {
        let name = format!("bool_{}", some_bools);
        interface = interface.add_p(f.property::<bool,_>(name, ()).on_get(|i,_| { i.append(true); Ok(()) }));
    }
    let interface = Arc::new(interface);

    for i in 0..9999 {
        let object_name = format!("/com/blah/storage/block/{}", i);
        let v_name = format!("lvol{}", i);

        let mut op = f.object_path(object_name, v_name).introspectable();

        op = op.add(interface.clone());
        tree = tree.add(op);
    }

    tree.set_registered(&c, true).unwrap();
    for _ in tree.run(&c, c.iter(1000)) {}
}

