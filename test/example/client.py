from coworks.cli import main
import sys

if __name__ == '__main__':
    sys.argv[1:] = ['export', '--app', 'tech_app', '--format', 'terraform', '--out', 'out.tf']
    main()
