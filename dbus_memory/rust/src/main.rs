extern crate dbus;

// Test dbus service in rust to get an idea of memory footprint.

use dbus::{Connection, BusType, NameFlag};
use dbus::tree::{Factory};

fn main() {
    let c = Connection::get_private(BusType::Session).unwrap();
    c.register_name("com.blah.storage", NameFlag::ReplaceExisting as u32).unwrap();

    let f = Factory::new_fn();
    let mut tree = f.tree();

    tree = tree.add(f.object_path("/com/blah/storage/block")
        .introspectable()
        .object_manager()            
        .add(
        f.interface("com.blah.storage.Manager").add_m(
            f.method("Version", |m,_,_| {
                let s = "0.0.1";
                Ok(vec!(m.method_return().append1(s)))
            }).outarg::<&str,_>("reply")
        )
    ));

    for i in 0..9999 {
        let object_name = format!("/com/blah/storage/block/{}", i);
        let v_name = format!("lvol{}", i);

        let mut op = f.object_path(object_name).introspectable();
        let mut interface = f.interface("com.blah.storage.BlockDevice")
            .add_m(f.method("Hello", |m,_,_| {
                    let s = format!("Hello {}!", m.sender().unwrap());
                    Ok(vec!(m.method_return().append1(s)))
                    }).outarg::<&str,_>("reply")
            );

        interface = interface.add_p(f.property("Name", v_name));
        interface = interface.add_p(f.property("uuid", "kQ1BLF-iBTn-FiHR-x8yI-DEqt-Kyd4-JfbadZ"));
        interface = interface.add_p(f.property("some_count", 0u32));
        
        for some_u64 in 0..5 {
            let n = format!("u64_{}", some_u64);
            interface = interface.add_p(f.property(n, 0u64));
        }

        for some_strings in 0..7 {
            let name = format!("string_d_{}", some_strings);
            let value = format!("some bogus data {}", some_strings);
            interface = interface.add_p(f.property(name, value));
        }

        for some_bools in 0..5 {
            let name = format!("bool_{}", some_bools);
            interface = interface.add_p(f.property(name, true));
        }

        op = op.add(interface);
        tree = tree.add(op);
    }

    tree.set_registered(&c, true).unwrap();
    for _ in tree.run(&c, c.iter(1000)) {}
}

