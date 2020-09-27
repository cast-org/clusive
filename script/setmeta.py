# Simple script to set a couple of metadata fields in an EPUB3.

import argparse
import datetime
import os
import tempfile
import zipfile

import dawn
import xml.etree.ElementTree as ET


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description='Set metadata in one or more EPUB files.\n'
            'Last-modification date will also be updated if any metadata is changed, '
            'or if the --moddate flag is specified.'
    )

    parser.add_argument("-t", "--title", action='store')
    parser.add_argument("-st", "--sorttitle", action='store')
    parser.add_argument("-a", "--author", action='store')
    parser.add_argument("-sa", "--sortauthor", action='store')
    parser.add_argument("-s", "--series", action='store')
    parser.add_argument("-l", "--language", action='store')
    parser.add_argument("-d", "--moddate", action='store_true')

    parser.add_argument('files', nargs='*')
    return parser


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()
    if not args.files:
        print('No files listed, nothing changed.')

    for file in args.files:
        print('File: %s' % file)
        # generate a temp file
        tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(file))
        os.close(tmpfd)

        # copy everything except OPF
        found = False
        with zipfile.ZipFile(file, 'r') as zin:
            with zipfile.ZipFile(tmpname, 'w') as zout:
                zout.comment = zin.comment  # preserve the comment
                for item in zin.infolist():
                    if item.filename.endswith('.opf'):
                        found = True
                        zout.writestr(item, update_metadata(zin.read(item.filename).decode('utf-8'), args))
                    else:
                        zout.writestr(item, zin.read(item.filename))
        if found:
            # os.rename(tmpname, file+'.new')
            # rename old file to backup
            os.rename(file, file + '.bak')
            os.rename(tmpname, file)
        else:
            print('  No opf file found in %s' % file)


def update_metadata(xmlstr: str, args) -> str:
    namesp = {
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }
    ET.register_namespace('', 'http://www.idpf.org/2007/opf')
    ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
    root = ET.fromstring(xmlstr)
    metadata = root.find('opf:metadata', namesp)
    ## These items are like:  <dc:title>ABC</dc:title>
    title = metadata.find('dc:title', namesp)
    author = metadata.find('dc:creator', namesp)
    language = metadata.find('dc:language', namesp)
    modified = False

    if metadata is not None:
        if args.title:
            if update_simple_metadata_item(metadata, 'title', title, args.title,
                                           '{http://purl.org/dc/elements/1.1/}title', None):
                modified = True
        if args.language:
            if update_simple_metadata_item(metadata, 'language', language, args.language,
                                           '{http://purl.org/dc/elements/1.1/}language', None):
                modified = True
        if args.author:
            if update_simple_metadata_item(metadata, 'author', author, args.author,
                                           '{http://purl.org/dc/elements/1.1/}creator', {'id': 'author'}):
                modified = True
        if args.sortauthor:
            if author is not None:
                auth_id = author.attrib.get('id')
                if auth_id:
                    # <meta property="file-as" refines="#author">
                    xpath = "./opf:meta[@property='file-as'][@refines='#%s']" % auth_id
                    sortauthor = metadata.find(xpath, namesp)
                    if sortauthor is not None:
                        print('  Mod. sortauthor: %s -> %s' % ("".join(sortauthor.itertext()), args.sortauthor))
                        sortauthor.text = args.sortauthor
                    else:
                        print('  Create sortauthor: -> %s' % args.sortauthor)
                        sortauthor = ET.SubElement(metadata, '{http://www.idpf.org/2007/opf}meta',
                                                   {'property': 'file-as', 'refines': '#' + auth_id})
                        sortauthor.text = args.sortauthor
                else:
                    print('  Author has no id')
        if modified or args.moddate:
            ## <meta property="dcterms:modified">2020-09-10T13:17:01Z</meta>
            mod_date = metadata.find('opf:meta[@property="dcterms:modified"]', namesp)
            now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            if mod_date is not None:
                print('  Mod. date: %s -> %s' % ("".join(mod_date.itertext()), now))
            else:
                print('  Add mod date: -> %s' % now)
                mod_date = ET.SubElement(metadata, '{http://www.idpf.org/2007/opf}meta',
                                         {'property': 'dcterms:modified'})
            mod_date.text = now

    else:
        print('  Metadata element not found')

    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode')


def update_simple_metadata_item(metadata, elt_name, elt, new_val, elt_spec, attributes):
    if elt is not None:
        old_val = "".join(elt.itertext())
        ### print('  Found language: ', "".join(elt.itertext()))
        if old_val == new_val:
            print('  %s unchanged' % elt_name)
            return False
        else:
            print('  Mod. %s: %s -> %s' % (elt_name, old_val, new_val))
    else:
        print('  Create %s: -> %s' % (elt_name, new_val))
        elt = ET.SubElement(metadata, elt_spec, attributes)
    elt.text = new_val
    return True


if __name__ == "__main__":
    main()
