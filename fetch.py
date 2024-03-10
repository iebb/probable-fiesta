#!/usr/bin/env python3
import datetime
import hashlib
import os
import re
import sys
import urllib.parse

import requests
from bs4 import BeautifulSoup, Comment

ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
metadata_identifier = "@@ CRAWLER METADATA @@"


class Crawler:
    def get_meta(self, base_link):
        if not (base_link.startswith("http://") or base_link.startswith("https://")):
            return
        save_location = Crawler.get_main_save_link(base_link)
        print(f"{base_link}:")
        if os.path.isfile(save_location):
            with open(save_location, "r", encoding="u8") as saved_file:
                soup = BeautifulSoup(saved_file, features="html.parser")
                if soup.children:
                    cmt = next(soup.children)
                    if cmt is Comment and cmt.startswith(metadata_identifier):
                        print(cmt.replace(metadata_identifier + "\n", ""))
                    else:
                        print(f"> No metadata recorded.")

        else:
            print(f"> {base_link} has not been crawled yet.")
        print("")

    @staticmethod
    def get_main_save_link(url):
        return re.sub('[:*?"<>|=]', '_', re.sub("https?://", "", url)).replace("/", "_") + ".html"

    def parse_url_inside_css(self, css_file, css_url, filename):
        url_patterns = re.findall(r'url\(["\']?([^)]*?)["\']?\)', css_file)
        for url in url_patterns:
            if url.startswith("data:"):
                continue
            elif url.startswith("https:") or url.startswith("http:"):
                css_file = css_file.replace(url, self.crawl_single_file(url))
            elif url.startswith("/"):
                css_abs_url = urllib.parse.urljoin(css_url, url)
                css_file = css_file.replace(url, self.crawl_single_file(css_abs_url))
            else:  # relative path
                if url:
                    css_abs_url = urllib.parse.urljoin(css_url, url)
                    target_url = urllib.parse.urljoin(filename, url)
                    self.crawl_single_file(css_abs_url, target_url)
        return css_file

    def crawl_single_file(self, url, filepath=None):
        if "://" not in url:
            return url
        # print("crawling resource", url)
        try:
            if not filepath:
                filepath = url.replace("://", "/")

            filepath = re.sub('[:*"<>|=&]', '_', filepath)

            if '#' in filepath:
                filepath = filepath.split("#")[0]

            # remove anchors

            filepath_parts = []

            for part in filepath.split("/"):
                if len(part) <= 48:
                    filepath_parts.append(part)
                else:  # for too lengthy path names use md5 instead
                    filepath_parts.append(hashlib.md5(part.encode("u8")).hexdigest())

            # aaa.css?q=1a2b3c => aaa.q_1a2b3c.css to preserve type. useful in type-based MIMEs
            if '?' in filepath_parts[-1]:  # contains ?
                filename, query = filepath_parts[-1].split("?", maxsplit=1)
                if "." in filename:  # contains extension:
                    filename_period_split = filename.split(".")
                    filename_period_split[-2] += "_" + query
                    filename = ".".join(filename_period_split)
                else:
                    filename += "_" + query
                filepath_parts[-1] = filename

            filepath = "/".join(filepath_parts)

            # is it already crawled?
            if os.path.isfile(filepath):
                return filepath

            crawled = requests.get(
                url,
                headers={'User-Agent': ua}
            )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            while os.path.isdir(filepath):
                filepath += "_"

            if filepath.endswith(".css"):
                print("it's a css so we need to parse inside")
                content = self.parse_url_inside_css(crawled.text, url, filepath)
                open(filepath, "w+", encoding="u8").write(content)
            else:
                open(filepath, "wb+").write(crawled.content)
            return filepath
        except Exception as e:
            print(f"ERROR Downloading Resources: {e}", file=sys.stderr)
            return url

    def crawl_page(self, base_link):
        if not (base_link.startswith("http://") or base_link.startswith("https://")):
            return

        try:

            # print("> crawling", base_link)
            parsed_url = urllib.parse.urlparse(base_link)
            save_location = Crawler.get_main_save_link(base_link)

            crawled = requests.get(
                base_link,
                headers={'User-Agent': ua}
            )
            soup = BeautifulSoup(crawled.text, features="html.parser")

            link_count = len(soup.find_all('a', href=True))
            img_count = 0

            for tag in soup.find_all('link', rel='stylesheet'):  # link-stylesheet tag
                if tag.has_attr('href'):
                    _href = urllib.parse.urljoin(base_link, tag['href'])
                    tag['href'] = self.crawl_single_file(_href)

            for tag in soup.find_all('link', rel='icon'):  # link-icon, for possibly favicon
                if tag.has_attr('href'):
                    _href = urllib.parse.urljoin(base_link, tag['href'])
                    tag['href'] = self.crawl_single_file(_href)

            for tag in soup.find_all('script', src=True):  # script tag, src
                _href = urllib.parse.urljoin(base_link, tag['src'])
                tag['src'] = self.crawl_single_file(_href)

            for tag in soup.find_all('style'):  # embedded styles. parse them for css urls
                self.parse_url_inside_css(str(tag), base_link, save_location)

            for tag in soup.find_all('img'):  # img tag, src
                img_count += 1
                if tag.has_attr('src'):
                    _href = urllib.parse.urljoin(base_link, tag['src'])
                    tag['src'] = self.crawl_single_file(_href)

                if tag.has_attr('srcset'):
                    modified = []
                    for srcset_item in tag['srcset'].split(","):
                        stripped = srcset_item.strip()
                        if len(stripped) == 2:
                            srcset_items = stripped.split(" ", maxsplit=2)
                            new_url = self.crawl_single_file(urllib.parse.urljoin(base_link, srcset_items[0]))
                            modified.append(f'{new_url}, {srcset_items[1]}')
                    tag['srcset'] = ", ".join(modified)

            # removing cross-origin tags, they are not supported in files

            for cross_origin_tag in ['script', 'img', 'audio', 'video', 'link']:
                for tag in soup.find_all(cross_origin_tag, crossorigin=True):
                    del tag['crossorigin']

            soup.insert(0, Comment("\n".join([
                metadata_identifier,
                f'site: {parsed_url.netloc}',
                f'num_links: {link_count}',
                f'images: {img_count}',
                f'last_fetch: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            ])))

            open(save_location, "w+", encoding="u8").write(str(soup))
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)


if __name__ == '__main__':
    if '--metadata' in sys.argv:
        for param in sys.argv[1:]:
            Crawler().get_meta(param)
    else:
        for param in sys.argv[1:]:
            Crawler().crawl_page(param)
