#! /usr/bin/env python3

import os
import sys
import argparse
import jinja2
import markdown

parser = argparse.ArgumentParser(description="Fill HTML frontend page template with some variables")
parser.add_argument("-T", "--title", help="title")
parser.add_argument("-l", "--legal-notice", help="URL of legal notice page")
parser.add_argument("-p", "--privacy", help="URL of privacy statement")
parser.add_argument("-t", "--template", help="template path")
parser.add_argument("-m", "--markdown-file", help="patch containing markdown content to be converted into HTML and inserted into the page")
args = parser.parse_args()

template_dir = os.path.dirname(os.path.abspath(args.template))
template_name = os.path.basename(args.template)
env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_dir),
                         trim_blocks=True,
                         autoescape=True
)
template = env.get_template(template_name)

html = None
if args.markdown_file:
    with open(args.markdown_file, "r") as md_file:
        html = markdown.markdown(md_file.read())

out = template.render(title=args.title, legal_notice=args.legal_notice, privacy=args.privacy, content=html)
sys.stdout.write(out)
