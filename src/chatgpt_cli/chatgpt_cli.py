import sys


def main() -> None:
    match len(sys.argv):
        case 1:
            print("Hello World!")
        case 2:
            print(f"Hello {sys.argv[1]}!")
        case _:
            print(f"Hello {', '.join(sys.argv[1:])}!")


if __name__ == "__main__":
    main()
