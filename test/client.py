from coworks.cli import main
import sys

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Client test script: Missing number argument")
        sys.exit()

    if sys.argv[1] == "0":
        sys.argv[1:] = ['--project-dir', 'example', 'export', '-m', 'example', '-a', 'app']
    elif sys.argv[1] == "1":
        sys.argv[1:] = ['export', '-m', 'example.example', '-a', 'app']

    elif sys.argv[1] == "2":
        sys.argv[1:] = ['export', '-m', 'biz.example', '-a', 'biz', '--format', 'sfn']
    elif sys.argv[1] == "3":
        sys.argv[1:] = ['export', '-m', 'biz.example', '-a', 'biz', '--format', 'sfn', '-b', 'small']
    elif sys.argv[1] == "4":
        sys.argv[1:] = ['--project-dir', 'biz', 'update', '-m', 'example', '-a', 'biz', '-b', 'complete']

    else:
        print(f"Undefined argument {sys.argv[1]}")
        sys.exit(1)
    main()
