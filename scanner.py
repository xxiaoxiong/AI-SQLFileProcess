import os


def scan_java_files(source_dir):
    """
    Recursively scan source_dir for .java files.
    Returns list of (abs_path, rel_path) tuples.
    rel_path is relative to source_dir (used to replicate directory structure).
    """
    source_dir = os.path.abspath(source_dir)
    results = []
    for root, dirs, files in os.walk(source_dir):
        for fname in files:
            if fname.lower().endswith('.java'):
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, source_dir)
                if os.path.getsize(abs_path) == 0:
                    continue
                results.append((abs_path, rel_path))
    return results
