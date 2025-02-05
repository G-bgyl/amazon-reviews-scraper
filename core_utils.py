import errno
from time import sleep

import json
import logging
import os
import re
import requests
from bs4 import BeautifulSoup

from banned_exception import BannedException
from constants import AMAZON_BASE_URL, MAX_BAN_RETRY

OUTPUT_DIR = 'comments'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def get_reviews_filename(product_id):
    filename = os.path.join(OUTPUT_DIR, '{}.json'.format(product_id))
    exist = os.path.isfile(filename)
    return filename, exist


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def persist_comment_to_disk(reviews):
    if len(reviews) == 0:
        return False
    product_id_set = set([r['product_id'] for r in reviews])
    assert len(product_id_set) == 1, 'all product ids should be the same in the reviews list.'
    product_id = next(iter(product_id_set))
    output_filename, exist = get_reviews_filename(product_id)
    if exist:
        return False
    mkdir_p(OUTPUT_DIR)
    # https://stackoverflow.com/questions/18337407/saving-utf-8-texts-in-json-dumps-as-utf8-not-as-u-escape-sequence/18337754
    with open(output_filename, 'w', encoding='utf-8') as fp:
        json.dump(reviews, fp, sort_keys=True, indent=4, ensure_ascii=False)
    return True


def extract_product_id(link_from_main_page):
    # e.g. B01H8A7Q42
    p_id = -1
    tags = ['/dp/', '/gp/product/']
    for tag in tags:
        try:
            p_id = link_from_main_page[link_from_main_page.index(tag) + len(tag):].split('/')[0]
        except:
            pass
    m = re.match('[A-Z0-9]{10}', p_id)
    if m:
        return m.group()
    else:
        return None


def get_soup_retry(url):
    from fake_useragent import UserAgent
    ua = UserAgent()
    UserAGR = ua.random
    if AMAZON_BASE_URL not in url:
        url = AMAZON_BASE_URL + url
    nap_time_sec = 1
    logging.debug('Script is going to sleep for {} (Amazon throttling). ZZZzzzZZZzz.'.format(nap_time_sec))
    sleep(nap_time_sec)

    header = {
        'User-Agent': UserAGR
    }
    logging.debug('-> to Amazon : {}'.format(url))
    isCaptcha = True
    try_cnt = 0
    while isCaptcha is True:
        out = requests.get(url, headers=header)
        assert out.status_code == 200
        soup = BeautifulSoup(out.content, 'lxml')
        if try_cnt >= MAX_BAN_RETRY:
            return soup

        if 'captcha' in str(soup):
            UserAGR = ua.random
            print('Bot has been detected... retrying ... use new identity: ', UserAGR)
            isCaptcha = True
        else:
            UserAGR = ua.random
            print('Bot bypassed')
            isCaptcha = False
            return soup
        try_cnt += 1


def get_soup(url):
    soup = get_soup_retry(url)
    return soup
