# creating paths to src and data folders in the repo
import sys
import pathlib
import os
import shutil

# basic imports for data retreival and manipulation
import requests
import pandas as pd
import numpy as np
import datetime as dt
import time
import re
import json

# importing api wrappers for reddit data
import praw
from psaw import PushshiftAPI

def get_api_instance(src_path):
    '''
    returns an instance of the psaw object initialized using praw
    
    parameters:
    --src_path: pathlib.path object pointing to the src directory or the directory containing api_credentials.txt
    
    returns:
    --s_api: an instance of pushift's psaw api
    '''
    # retrieve api credentials from .gitignore'd text file
    secrets_path = src_path / 'api_credentials.txt'
    secrets_txt = open(secrets_path, 'r')

    my_id = secrets_txt.readline().split('=')[1].rstrip()
    my_secret = secrets_txt.readline().split('=')[1].rstrip()
    my_agent = secrets_txt.readline().split('=')[1].rstrip()

    secrets_txt.close()

    # create a praw and pushshitft instances
    reddit = praw.Reddit(
         client_id=my_id,
         client_secret=my_secret,
         user_agent=my_agent)

    s_api = PushshiftAPI(reddit)
    
    return s_api

def establish_binary_directory(directory_path):
    '''
    creates a directory structure to store the dataset
    
    Parameters:
        -- directory_path: a pathlib.path object where the directory is to be created
        
    Returns:
        None
    '''
    os.mkdir(str(directory_path / 'binary_tts'))
    for split in ['train', 'val', 'test']:
        os.mkdir(str(directory_path / 'binary_tts' / split))
        for category in ['digital', 'non_digital']:
            os.mkdir(str(directory_path / 'binary_tts' / split / category))

def download_and_store_binary(toc, store_path, ttvs):
    '''
    downloads and stores images in train/test/val split directories
    
    parameters:
    --toc: list of dictionaries containing the critical meta-data for the images to be downloaded
    --store_path: pathlib.path object pointing to the directory containing the train/test/val folders
    --ttvs: list of ints representing the number of images in each split [train, test, val]
    
    returns:
    None
    '''
    btrain_path = store_path / 'train'
    binary_balance_train = get_dir_balance(btrain_path)
    btest_path = store_path / 'test'
    binary_balance_test = get_dir_balance(btest_path)
    bval_path = store_path / 'val'
    binary_balance_val = get_dir_balance(bval_path)
    for category in ['digital', 'non_digital']:
        count = 1
        for post in toc:
            if (post['medium'] == 'digital' and category == 'digital') or (post['medium'] != 'digital' and category == 'non_digital'):
                print(f"downloading {post['id']} with {sum(ttvs) - count} remaining in {category}")
                if binary_balance_train[category] < ttvs[0]:
                    download_path = btrain_path / category
                    binary_balance_train[category] += download_image(post, download_path)
                elif binary_balance_test[category] < ttvs[1]:
                    download_path = btest_path / category
                    binary_balance_test[category] += download_image(post, download_path)
                elif binary_balance_val[category] < ttvs[2]:
                    download_path = bval_path / category
                    binary_balance_val[category] += download_image(post, download_path)
                count += 1

def download_image(post, path):
    '''
    downloads images from the provided url and names the file with the post id the image came from
    
    parameters:
    --post: a dictionary containing the meta-data for the image to be downloaded
    --path: pathlib.path object pointing to the directory where the image should be downloaded to
    
    returns:
    int: returns 1 if file succesfully downloaded, returns 0 is the file already exists
    '''
    file_name = f"{post['id']}.{post['url'][-3:]}"
    file_path = path / file_name
    if file_path.is_file():
        print(f'{file_name} already exists')
        return 0
    else:
        try:
            response = requests.get(post['url'])
            file = open(str(file_path), "wb")
            file.write(response.content)
            file.close()
            return 1
        except:
            print('error downloading, trying again')
            download_image(post, path)
            
def get_wordlists():
    '''
    returns a dictionary containing regex patterns of the keywords for each class stored in a dictionary
    '''
    wordlists = {'digital': ['digital', 'adobe', 'photoshop', 'procreate', 'wacom', 'tablet', 'illustrator', '3d', 'vector'],
                 'paint': ['acrylic', 'oil', 'watercolor', 'water color', 'watercolour', 'water colour'],
                 'non_ink_drawing': ['pencil', 'colored pencil', 'coloredpencil', 'color pencil', 'colorpencil', 'colour pencil', 'colourpencil', 'coloured pencil', 'colouredpencil', 'graphite', 'charcoal', 'chalk'],
                 'ink': ['pen(?!cil)', 'marker', 'ink'],
                 'sculpture': ['clay', 'string', 'sculpture', 'wire', 'nail', 'glass', 'yarn', 'metal', 'copper'],
                 'mixed_medium': []}
    return wordlists

def validate_submission(post):
    '''
    function for determining if a post is formated in a way that can be parsed properly
    
    Parameters:
    -- post: praw.submission object to be validated
    
    Returns:
    -- Boolean: True if post has valid formatting, False if not
    '''
    if post.selftext in ['[deleted]', '[removed]']:
        return False
    if post.upvote_ratio < .4:
        return False
    link_format = 'https://i\.redd\.it/.{13}\.(jpg|png)'
    corpus = []
    wordlists = get_wordlists()
    for value in wordlists.values():
        corpus.extend(value)
    title = post.title.lower().split(',')
    if len(title) == 4:
        medium = title[2].strip()
        if medium == 'me':
            medium = title[1].strip()
        if re.match(link_format, post.url):
            for word in corpus:
                if medium.find(word) >= 0:
                    return True
    return False
    
def extract_medium_from_title(title):
    '''
    identifies the medium given the title of the post
    '''
    medium_counter = 0
    medium_type = 'other'
    title_split = title.lower().split(',')
    medium = title_split[2].strip()
    if medium == 'me':
        medium = title_split[1].strip()
    wordlists = get_wordlists()
    for item in wordlists.items():
        for word in item[1]:
            if re.search(word, medium) != None:
                medium_type = item[0]
                medium_counter += 1
                break
    if medium_counter > 1:
        return 'mixed_medium'
    else:
        return medium_type

def make_post_dict(post):
    '''
    creates and returns a dict containing relevant data from a post
    '''
    post_dict = {'title': post.title,
                 'medium': extract_medium_from_title(post.title),
                 'url': post.url, 
                 'id': post.id,
                 'unix_time': int(post.created_utc),
                 'self_text': post.selftext,
                 'post': post}
    return post_dict

def make_post_dict_no_obj(post):
    '''
    creates and returns a dict containing relevant data from a post without the submission object
    '''
    post_dict = {'title': post.title,
                 'medium': extract_medium_from_title(post.title),
                 'url': post.url, 
                 'id': post.id,
                 'unix_time': int(post.created_utc)}
    return post_dict

def fetch_balanced_submissions(n_to_fetch, s_api, date=int(dt.datetime.now().timestamp()), current_balance=None, binary=False):
    '''
    creates a list of praw post objects with a balanced number of each class
    
    parameters:
    --n_to_fetch: int, number of posts to collect
    --s_api: an instance of the psaw object
    --date: int, unix timestamp for the date from which the search should begin, defaults to the current date and time
    --current_balance: dict, dictionary containing the current number of images in each class
    --binary: boolean indicating whether or not the dataset is a binary classification
    
    returns:
    a list of praw submission objects
    '''
    class_counts = {}
    # taking into account the current class balance if data has already been downloaded
    if type(current_balance) == dict:
        class_counts = current_balance
    elif binary:
        class_counts = {'digital': 0, 'non_digital': 0}
        subclass_counts = {'ink': 0, 'non_ink_drawing': 0, 'paint': 0, 'sculpture': 0}
    else:
        class_counts = dict(zip(list(get_wordlists().keys()), [0 for _ in get_wordlists().keys()]))
    start_epoch = date
    data_size = n_to_fetch + sum(list(class_counts.values()))
    n_per_class = int(data_size / len(class_counts.keys()))
    print((n_per_class, data_size))
    collected_posts = []
    while len(collected_posts) < n_to_fetch:
        print(f'polling pushshift for {n_to_fetch - len(collected_posts)} more posts before {start_epoch}')
        batch = list(s_api.search_submissions(before=start_epoch, subreddit='Art', limit=1000))
        for post in batch:
            if validate_submission(post):
                if not binary:
                    if class_counts[extract_medium_from_title(post.title)] < n_per_class:
                        collected_posts.append(post)
                        class_counts[extract_medium_from_title(post.title)] += 1
                else:
                    if extract_medium_from_title(post.title) == 'digital' and class_counts['digital'] < n_per_class:
                        collected_posts.append(post)
                        class_counts['digital'] += 1
                    elif extract_medium_from_title(post.title) in ['ink', 'non_ink_drawing', 'paint', 'sculpture'] and class_counts['non_digital'] < n_per_class:
                        if subclass_counts[extract_medium_from_title(post.title)] < (n_per_class / 4):
                            
                            collected_posts.append(post)
                            subclass_counts[extract_medium_from_title(post.title)] += 1
                            class_counts['non_digital'] += 1
        start_epoch = int(batch[-1].created_utc)
    return collected_posts

def get_dir_balance(dir_path):
    '''
    returns a dictionary of the current class balance of images stored in the local directory
    
    parameters:
    --dir_path: pathlib.path object pointing to the directory containing the currentyly stored images
    
    returns:
    dictionary
    '''
    current_b = {}
    with os.scandir(dir_path) as t_scan:
        for class_name in t_scan:
            if class_name.is_dir():
                class_path = dir_path / class_name.name
                current_b[class_name.name] = len(list(os.listdir(class_path)))
    return current_b

# function for locating posts by id for data exploration purposes
def find_submission_dict_by_id(id_str, table_of_contents):
    '''
    searches the table of contents for a specific post given the post id
    
    parameters:
    --id_str: string containing the post id
    --table_of_contents: list of dictionaries containing the critical meta-data for each post
    
    returns:
    dictionary containing the critical meta-data for the matching post
    '''
    for post in table_of_contents:
        if post['id'] == id_str:
            return post
