extern crate dbus;

// Test dbus service in rust to ensure we get the expected values.

use dbus::tree::{DataType, Factory};
use dbus::{BusType, Connection, NameFlag};
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

static NAME: &str = "com.blah.sizecheck";
static PATH: &str = "/com/blah/sizecheck";

fn main() {
    let c = Connection::get_private(BusType::Session).unwrap();
    c.register_name(NAME, NameFlag::ReplaceExisting as u32)
        .unwrap();

    let f = Factory::new_fn::<OPData>();
    let mut tree = f.tree(());

    tree = tree.add(
        f.object_path(PATH, "".to_owned())
            .introspectable()
            .object_manager()
            .add(
                f.interface(format!("{}.Manager", NAME), ()).add_m(
                    f.method("Version", (), |m| {
                        let s = "0.0.1";
                        Ok(vec![m.msg.method_return().append1(s)])
                    })
                    .outarg::<&str, _>("reply"),
                ),
            ),
    );

    let mut interface = f.interface(format!("{}.Values", NAME), ()).add_m(
        f.method("Hello", (), |m| {
            let s = format!("Hello {}!", m.msg.sender().unwrap());
            Ok(vec![m.msg.method_return().append1(s)])
        })
        .outarg::<&str, _>("reply"),
    );

    interface = interface.add_p(f.property::<&str, _>("some_string", ()).on_get(|i, _| {
        i.append("ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789");
        Ok(())
    }));

    interface = interface.add_p(f.property::<u8, _>("some_u8", ()).on_get(|i, _| {
        i.append(0x1Fu8);
        Ok(())
    }));

    interface = interface.add_p(f.property::<u16, _>("some_u16", ()).on_get(|i, _| {
        i.append(0x0102u16);
        Ok(())
    }));

    interface = interface.add_p(f.property::<u32, _>("some_u32", ()).on_get(|i, _| {
        i.append(0x01020304u32);
        Ok(())
    }));

    interface = interface.add_p(f.property::<u64, _>("some_u64", ()).on_get(|i, _| {
        i.append(0x0102030405060708u64);
        Ok(())
    }));

    interface = interface.add_p(f.property::<i16, _>("some_i16", ()).on_get(|i, _| {
        i.append(-32768i16);
        Ok(())
    }));

    interface = interface.add_p(f.property::<i32, _>("some_i32", ()).on_get(|i, _| {
        i.append(-2147483648i32);
        Ok(())
    }));

    interface = interface.add_p(f.property::<i64, _>("some_i64", ()).on_get(|i, _| {
        i.append(-9223372036854775808i64);
        Ok(())
    }));

    interface = interface.add_p(f.property::<bool, _>("some_true_bool", ()).on_get(|i, _| {
        i.append(true);
        Ok(())
    }));

    interface = interface.add_p(f.property::<bool, _>("some_false_bool", ()).on_get(|i, _| {
        i.append(false);
        Ok(())
    }));

    interface = interface.add_p(f.property::<f64, _>("some_f64", ()).on_get(|i, _| {
        i.append(std::f64::MAX);
        Ok(())
    }));

    let interface = Arc::new(interface);

    for i in 0..1 {
        let object_name = format!("{}/{}", PATH, i);
        let v_name = format!("validate{}", i);

        let mut op = f.object_path(object_name, v_name).introspectable();

        op = op.add(interface.clone());
        tree = tree.add(op);
    }

    tree.set_registered(&c, true).unwrap();
    for _ in tree.run(&c, c.iter(1000)) {}
}
