#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Rust 'use' check aka "RUC" for project stratis style guide.
import sys


def check_use(file_name):
    """
    Using the supplied file name it opens it and checks for 'use' statements
    in rust code, to see if they conform to the style guide for stratis project.
    :param file_name: File name to open
    :return: True if all is well, else False
    """
    existing = {}
    list_order = []
    result = True
    multi_line_use = None
    prev_cfg_test = False

    with open(file_name) as source_code:
        line_number = 0
        for line in source_code:
            line_number += 1

            if not prev_cfg_test and line.startswith('use') or multi_line_use:
                # We can have consolidated use statements which cross a number
                # of lines, handle them.
                if multi_line_use is None and '{' in line and '}' not in line:
                    # We have the beginning of a multi-line use
                    multi_line_use = line.rstrip().lstrip()
                    continue
                elif multi_line_use:
                    # Reconstruct to one line
                    line = line.lstrip().rstrip()
                    line = multi_line_use + ' ' + line
                    if '}' in line:
                        # We are complete
                        multi_line_use = None
                    else:
                        continue

                s = line.rstrip(";\n}")
                if '{' in s:
                    # Process multi use
                    prefix, use_string = s.split('{')
                    use_list = use_string.split(",")
                    use_list = [x.strip(' ') for x in use_list]
                    use_string = ", ".join(use_list)

                    table_entry = prefix.rstrip("::").split()[1]

                    sorted_list = sorted(use_list)
                    sorted_string = ", ".join(sorted_list)

                    if use_string != sorted_string:
                        print("ERROR SORT: %s %d [%s]" % (
                            file_name, line_number, sorted_string))
                        result = False
                    else:
                        # We need to store the specific use to ensure no other
                        if table_entry in existing:
                            print(
                                "ERROR DUPE: %s %d Duplicate base use "
                                "%s, prev = %s" % (
                                    file_name, line_number, table_entry,
                                    existing[table_entry]))
                            result = False
                        else:
                            existing[table_entry] = s

                    list_order.append(table_entry)

                else:
                    if " as " not in s:
                        table_entry = s.split()[1]
                        raw_entry = table_entry

                        if "::" in table_entry:
                            use_parts = table_entry.split("::")
                            table_entry = "::".join(use_parts[: -1])

                            if table_entry in existing:
                                print(
                                    "ERROR DUPE: %s %d Duplicate base use "
                                    "%s, prev = %s" % (
                                        file_name, line_number, table_entry,
                                        existing[table_entry]))
                                result = False
                            else:
                                existing[table_entry] = s

                            list_order.append(raw_entry)

            else:
                # We hit something other than use, see if the use statements are
                # good
                if list_order:
                    sorted_use_lines = sorted(list_order)
                    list_order_str = ", ".join(sorted_use_lines)
                    list_order_existing_str = ", ".join(list_order)
                    if list_order_existing_str != list_order_str:
                        print("ERROR LINE ORDERING: %s %s != %s" % (
                            file_name, list_order_existing_str, list_order_str))
                        result = False

                list_order = []

                # Test code uses mess with our rules, lets ignore them for now
                if line.startswith("#[cfg(test)]"):
                    prev_cfg_test = True
                    continue

            prev_cfg_test = False

        return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("syntax: ruc.py <rust file>\n")
        sys.exit(2)
    if not check_use(sys.argv[1]):
        sys.exit(1)
    sys.exit(0)
