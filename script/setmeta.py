# Simple script to set a couple of metadata fields in an EPUB3.

import argparse
import os
import tempfile
import zipfile

import dawn
import xml.etree.ElementTree as ET

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description="Set metadata in one or more EPUB files."
    )

    parser.add_argument("-t", "--title", action='store')
    parser.add_argument("-st", "--sorttitle", action='store')
    parser.add_argument("-a", "--author", action='store')
    parser.add_argument("-sa", "--sortauthor", action='store')
    parser.add_argument("-s", "--series", action='store')

    parser.add_argument('files', nargs='*')
    return parser


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()
    if not args.files:
        print('No files listed, nothing changed.')

    print('Title: %s' % args.title)

    for file in args.files:
        print('File: %s' % file)
        # generate a temp file
        tmpfd, tmpname = tempfile.mkstemp(dir=os.path.dirname(file))
        os.close(tmpfd)

        # copy everything except OPF
        found = False
        with zipfile.ZipFile(file, 'r') as zin:
            with zipfile.ZipFile(tmpname, 'w') as zout:
                zout.comment = zin.comment # preserve the comment
                for item in zin.infolist():
                    if item.filename.endswith('.opf'):
                        found = True
                        zout.writestr(item, update_metadata(zin.read(item.filename), args))
                        print('updated')
                    else:
                        zout.writestr(item, zin.read(item.filename))
        if found:
            os.rename(tmpname, file+'.new')
            # rename old file to backup
            #os.rename(file, file+'.bak')
            #os.rename(tmpname, file)
        else:
            print('No opf file found in %s' % file)


def update_metadata(xmlstr : str, args) -> str:
    namesp = {
        'opf' : 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }
    ET.register_namespace('', 'http://www.idpf.org/2007/opf')
    ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
    root = ET.fromstring(xmlstr)
    metadata = root.find('opf:metadata', namesp)
    title = metadata.find('dc:title', namesp)
    author = metadata.find('dc:creator', namesp)

    if metadata is not None:
        if args.title:
            if title is not None:
                print('mod. title: %s -> %s' % ("".join(title.itertext()), args.title))
                title.text = args.title
            else:
                print('title metadata not found')
        if args.author:
            if author is not None:
                print ('mod. author: %s -> %s' % ("".join(author.itertext()), args.author))
                author.text = args.author
            else:
                print('create author: -> %s' % args.author)
                author = ET.SubElement(metadata, '{http://purl.org/dc/elements/1.1/}creator', {'id': 'author'})
                author.text = args.author
        if args.sortauthor:
            if author is not None:
                auth_id = author.attrib.get('id')
                if auth_id:
                    # <meta property="file-as" refines="#author">
                    xpath = "./opf:meta[@property='file-as'][@refines='#%s']" % auth_id
                    sortauthor = metadata.find(xpath, namesp)
                    if sortauthor is not None:
                        print ('mod. sortauthor: %s -> %s' % ("".join(sortauthor.itertext()), args.sortauthor))
                        sortauthor.text = args.sortauthor
                    else:
                        print('create sortauthor: -> %s' % args.sortauthor)
                        sortauthor = ET.SubElement(metadata, '{http://www.idpf.org/2007/opf}meta',
                                                   {'property': 'file-as', 'refines': '#'+auth_id})
                        sortauthor.text = args.sortauthor
                else:
                    print('author has no id')
    else:
        print('metadata element not found')

    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding='unicode')


if __name__ == "__main__":
    main()
