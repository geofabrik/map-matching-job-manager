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
parser.add_argument("-u", "--url-prefix", help="prefix to put in front of all API URLs. Set this parameter to 'https://api.tld/api/' to get from '/status' to 'https://api.tld/api/status'",
        default=None, type=str)
args = parser.parse_args()

template_dir = os.path.dirname(os.path.abspath(args.template))
template_name = os.path.basename(args.template)
env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_dir),
                         trim_blocks=True,
                         autoescape=True
)
template = env.get_template(template_name)

md_env = jinja2.Environment(loader=jinja2.BaseLoader, autoescape=False)

html_in = None
if args.markdown_file:
    with open(args.markdown_file, "r") as md_file:
        html_in = markdown.markdown(md_file.read())

html = html_in
if args.url_prefix:
    md_template = md_env.from_string(html_in)
    html = md_template.render(url_prefix=args.url_prefix)

out = template.render(title=args.title, legal_notice=args.legal_notice, privacy=args.privacy, content=html)
sys.stdout.write(out)
