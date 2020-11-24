# creating paths to src and data folders in the repo
import sys
import pathlib
import os
import shutil
src_path = pathlib.Path().absolute().parent / "src"
data_path = pathlib.Path().absolute().parent / "data"

# add src path to sys.path so it is searched in import statements
sys.path.append(str(src_path))

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

# retrieve api credentials from .gitignore'd text file
secrets_path = src_path / 'api_credentials.txt'
secrets_txt = open(secrets_path, 'r')

my_id = secrets_txt.readline().split('=')[1].rstrip()
my_secret = secrets_txt.readline().split('=')[1].rstrip()

secrets_txt.close()

# create a praw and pushshitft instances
reddit = praw.Reddit(
     client_id=my_id,
     client_secret=my_secret,
     user_agent="test_script by u/Mizule_RL"
 )

s_api = PushshiftAPI(reddit)

def get_wordlists():
    '''
    returns a dictionary containing regex patterns of the keywords for each class
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

def fetch_submissions(min_posts, date = int(dt.datetime.now().timestamp())):
    start_epoch = date
    data_size = min_posts

    collected_posts = []
    while len(collected_posts) < data_size:
        print(f'polling pushshift for {data_size - len(collected_posts)} more posts before {start_epoch}')
        batch = list(s_api.search_submissions(before=start_epoch, subreddit='Art', limit=1000))
        for post in batch:
            if validate_submission(post):
                collected_posts.append(post)
        start_epoch = int(batch[-1].created_utc)
    return collected_posts

# functions for locating posts by id for data exploration purposes

def find_submission_dict_by_id(id_str):
    for post in table_of_contents:
        if post['id'] == id_str:
            return post
        
def find_submission_obj_by_id(id_str):
    for post in table_of_contents:
        if post['id'] == id_str:
            return post['post']