import toml
import sys


def bump_version(version, part):
    major, minor, patch = map(int, version.split("."))
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError("Part must be 'major', 'minor', or 'patch'")
    return f"{major}.{minor}.{patch}"


def update_version_file(file_path, part):
    with open(file_path, "r") as f:
        data = toml.load(f)

    current_version = data["project"]["version"]
    new_version = bump_version(current_version, part)
    data["project"]["version"] = new_version

    with open(file_path, "w") as f:
        toml.dump(data, f)

    print(f"Version updated from {current_version} to {new_version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version_interactive.py <path_to_pyproject.toml>")
        sys.exit(1)

    file_path = sys.argv[1]
    print("Select the part to bump:")
    print("1. Major")
    print("2. Minor")
    print("3. Patch")
    choice = input("Enter the number (1/2/3): ").strip()

    part_map = {"1": "major", "2": "minor", "3": "patch"}
    part = part_map.get(choice)
    if not part:
        print("Invalid choice. Must be 1, 2, or 3.")
        sys.exit(1)

    update_version_file(file_path, part)
