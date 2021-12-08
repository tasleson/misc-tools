#!/usr/bin/python3
from datetime import datetime, timezone
import os
import sys
import stat
import subprocess

# Walk a directory structure and add each file to a git repo that has author &
# commit date which matches the file mtime.  Used to seed a source tree that
# was never under source control.

COMMIT_COMMENT = "Initial commit"
GIT_BASE_DIR = None


def process_directory(some_dir):
    for root, subdirs, files in os.walk(some_dir):
        for s in subdirs:
            process_directory(s)

        for f in files:
            file_path = os.path.join(root, f)
            s = os.stat(file_path)

            d = datetime.fromtimestamp(s.st_mtime, tz=timezone.utc).strftime(
                "%a %b %d %H:%M:%S %G"
            )

            os.environ["GIT_AUTHOR_DATE"] = d
            os.environ["GIT_COMMITTER_DATE"] = d

            # Add the file
            subprocess.run(["git", "add", file_path], cwd=GIT_BASE_DIR)
            subprocess.run(
                ["git", "commit", "-a", "-s", "-m %s: %s" % (COMMIT_COMMENT, f)],
                cwd=GIT_BASE_DIR,
                env=os.environ,
            )


if __name__ == "__main__":

    GIT_BASE_DIR = os.path.abspath(sys.argv[1])
    src_dir = os.path.abspath(sys.argv[2])
    COMMIT_COMMENT = sys.argv[3]

    process_directory(src_dir)
