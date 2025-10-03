COMMAND_KNOWLEDGE_BASE = {
    "sudo": {
        "description": "Executes a command with superuser (root) privileges.",
        "danger_level": "high"
    },
    "rm": {
        "description": "Removes (deletes) files or directories.",
        "danger_level": "medium",
        "flags": {
            "-r": "Removes directories and their contents recursively.",
            "-f": "Forces the removal of files without prompting for confirmation.",
            "-i": "Prompts for confirmation before every removal."
        }
    },
    "ls": {
        "description": "Lists directory contents.",
        "danger_level": "low",
        "flags": {
            "-l": "Uses a long listing format.",
            "-a": "Shows all files, including hidden files (starting with '.').",
            "-h": "With -l, prints sizes in human readable format (e.g., 1K 234M 2G)."
        }
    },
    "chmod": {
        "description": "Changes the permissions of a file or directory.",
        "danger_level": "low"
    },
    "curl": {
        "description": "Transfers data from or to a server, using one of the supported protocols (HTTP, HTTPS, FTP, etc.).",
        "danger_level": "medium"
    },
    "wget": {
        "description": "A non-interactive network downloader.",
        "danger_level": "medium"
    },
    "bash": {
        "description": "The Bourne-Again SHell, a command language interpreter.",
        "danger_level": "medium"
    },
    "sh": {
        "description": "The standard command language interpreter.",
        "danger_level": "medium"
    },
    ":(){ :|:& };:": {
        "description": "A fork bomb. It is a denial-of-service attack where a process continually replicates itself to deplete available system resources, slowing down or crashing the system.",
        "danger_level": "critical"
    },
    "grep": {
        "description": "Searches for patterns in text files.",
        "danger_level": "low",
        "flags": {
            "-i": "Ignores case distinctions in patterns and data.",
            "-v": "Inverts the sense of matching, to select non-matching lines.",
            "-r": "Recursively searches subdirectories."
        }
    },
    "find": {
        "description": "Searches for files in a directory hierarchy.",
        "danger_level": "low",
        "flags": {
            "-name": "Searches for files with a specific name.",
            "-type": "Searches for files of a specific type (e.g., f for file, d for directory).",
            "-delete": "Deletes found files. This is a dangerous flag."
        }
    },
    "awk": {
        "description": "A versatile programming language for working on files.",
        "danger_level": "low",
        "flags": {
            "-F": "Specifies a field separator."
        }
    }
}
