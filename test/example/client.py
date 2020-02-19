from coworks.cli import main
import sys

if __name__ == '__main__':
    sys.argv[1:] = ['export', '--app', 'app', '--module', 'odoo', '--out', 'odoo.tf']
    main()
