"""(J)ust(A)nother(WA)llhaven(S)craper (jawas)"""
#!/usr/bin/env python3

import multiprocessing as mp
from argparse import RawTextHelpFormatter
from bs4 import BeautifulSoup
import requests
import os
import argparse
import time
import logging

logger = logging.getLogger('main')
args = ''

def main():
    """Main"""

    parser = argparse.ArgumentParser(
        description="Download wallpapers from wallhaven.cc, on the CLI",
        formatter_class=RawTextHelpFormatter,
        epilog="Examples:\n"
        "jawas -q 'the witcher' -d /home/user/pictures -r 1920x1080 -e -l 2000 -s sketchy -j 2\n"
        "jawas --query 'linux' --directory /tmp/"
    )

    parser.add_argument('-q', '--query', required=True,
                        help="Specifies the search query on wallhaven.")
    parser.add_argument('-d', '--directory',
                        help="Specifies the destination save path for downloaded wallpapers. "
                        "Omit this option to save in the current directory.")
    parser.add_argument('-r', '--resolution',
                        help="Specifies the resolution for downloaded wallpapers, if available. "
                        "Omit this option to download any found wallpaper, "
                        "regardless of resolution.")
    parser.add_argument('-e', '--exact', action='store_true',
                        help="Only download wallpapers in the exact resolution defined "
                        "by '-r' or '--resolution'.")
    parser.add_argument('-l', '--limit', type=int, default=float("inf"),
                        help="Specifies the number of wallpapers to download. "
                        "Omit this option to download all available wallpapers")
    parser.add_argument('-s', '--safety', choices=['sketchy', 'sfw'],
                        help="Specifies whether to download SFW or SFW/Sketchy wallpapers. "
                        "Omit this option to only download SFW wallpapers")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Specifies level of output for the application (INFO, DEBUG, ERROR)")
    parser.add_argument('-x', '--random', action='store_true',
                        help="Download a random wallpaper from wallhaven")
    parser.add_argument('-p', '--popular', action='store_true',
                        help="Download from the most popular wallpapers on wallhaven.cc")
    parser.add_argument('-j', '--pool', type=int, choices=range(0, mp.cpu_count()), default=1,
                        help="Specifies the number of processor cores to allocate for "
                        "parallel tasks. Defaults to 1 if not specified.")

    args = parser.parse_args()

    # init multiprocessor based on passed CPU cores
    pool = mp.Pool(args.pool)

    if not args.directory:
        os.chdir(str(os.getcwd()))
    else:
        os.chdir(str(args.directory))
    print(str(os.getcwd()))

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # 1. construct initial link to follow, using passed args
    search_term = "https://wallhaven.cc/search?q="

    term_split = args.query.split()
    for word in term_split:
        # if last split, omit final plus sign
        if word == term_split[len(term_split)-1]:
            search_term += word + '&categories=111'
        else:
            search_term += word + '+'
    if str(args.safety).lower() == 'sketchy':
        search_term += '&purity=110'
    else:
        search_term += '&purity=100'
    if args.resolution:
        if args.exact:
            search_term += '&resolutions=' + str(args.resolution).lower()
        else:
            search_term += '&atleast=' + str(args.resolution).lower()
            
    search_term += '&sorting=relevance&order=desc&page=1'

    # 2. retrieve paginated preview links for wallpapers
    print("Retrieving links from: " + search_term)
    print("This may take a few minutes...")
    image_links = get_links(search_term, args.limit)

    # 3. retrieve direct, src links to wallpaper images
    #src_links = pool.map(grab_src, image_links)
    #src_links = list.extend(pool.map(grab_src, image_links))
    src_links = []
    for image in image_links:
        src_links.extend(grab_src(image))
        #time.sleep(1)

    # 4. download wallpaper src links to specified or current dir
    pool.map(save_image, src_links)
    #for image_links in src_links:
        #save_image(image_links)

##################################################

def get_links(search_term, limit):
    """Get requested wallpaper links, based on constructed search term"""
    links = []
    image_count = 0
    page_count = 1
    page_request = requests.get(search_term, headers = {'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(page_request.text, features="html.parser")
    preview_links = soup.findAll("a", { "class": "preview" } )
    #image_count = preview_links.len()

    if not preview_links:
        print("No wallpapers found for the specified search/options, exiting...")
        exit(0)

    # while list of preview links not empty (meaning we have more wallpapers to get)
    # and we've not exceeded the link retrieval limit (if applicable)
    while preview_links and image_count <= limit:
        for image in preview_links:
            links.append(image.get('href'))
            image_count+=1
        page_count+=1
        search_term = search_term.split('page=')[0] + 'page=' + str(page_count)
        print("Parsing " + search_term)
        #logger.debug('Parsing ' + search_term)
        page_request = requests.get(search_term, headers = {'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(page_request.text, features="html.parser")
        preview_links = soup.findAll("a", { "class": "preview" } )

        # sleep 1 second to avoid rate-limiting on requests
        time.sleep(1)

    return links

##################################################

def grab_src(preview_link):
    """Assemble direct image links from preview links"""
    src_links = []
    request = requests.get(preview_link)

    # keep requesting in event of 429 response (this is not nice)
    while request.status_code == 429:
        request = requests.get(preview_link)
    soup = BeautifulSoup(request.text, features="html.parser")
    for preview_link in soup.findAll(id='wallpaper'):
        src_links.append(preview_link.get('src'))
        print('Added: ' + src_links[-1])
    return src_links

##################################################

def save_image(image_link):
    """Write images to local filesystem"""
    #logger.debug('Saving file:')
    filename = str(image_link).split('-')[-1]
    print (str(os.getcwd()))
    print('Saving ' + filename + ' -----> ' + str(os.getcwd()) + '/' + filename)
    open(filename, 'wb').write(requests.get(image_link).content)

##################################################

try:
    main()
except KeyboardInterrupt:
    print("Exiting due to user request...")
    exit(0)
