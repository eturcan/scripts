'''
Created on Jul 24, 2018
Updated on Oct 23, 2018

@author: ezotkina
@author: reskander
'''
# coding=utf-8
# -*- coding: utf-8 -*-

import sys
import re
import unicodedata
import string

english_alphabet = "abcdefghijklmnopqrstuvwxyz"
english_vowels = "aeiou"

swahili_alphabet = "abcdefghijklmnopqrstuvwxyz"
swahili_vowels = "aeiou"

tagalog_alphabet = "abcdefghijklmnopqrstuvwxyz"
tagalog_vowels = "aeiou"

somali_alphabet = "abcdefghijklmnopqrstuvwxyz'"
somali_vowels = "aeiou"

lithuanian_alphabet = "aąbcčdeęėfghiįyjklmnoprsštuųūvzž"
lithuanian_vowels = "aąeęėiįouųū"

alphabet_map = {}
alphabet_map["ENG"] = english_alphabet;
alphabet_map["TGL"] = tagalog_alphabet;
alphabet_map["SWA"] = swahili_alphabet;
alphabet_map["SOM"] = somali_alphabet;
alphabet_map["LIT"] = lithuanian_alphabet;

vowels_map = {}
vowels_map["ENG"] = english_vowels;
vowels_map["TGL"] = tagalog_vowels;
vowels_map["SWA"] = swahili_vowels;
vowels_map["SOM"] = somali_vowels;
vowels_map["LIT"] = lithuanian_vowels;

''' Special cxases not handled by the default unicode undiacritization '''
character_mappings = {
    'ą': 'a',
    'č': 'c',
    'ę': 'e',
    'ė': 'e',
    'į': 'i',
    'š': 's',
    'ų': 'u',
    'ū': 'u',
    'ž': 'z',
}

def normalize(language, text, remove_repetitions, remove_vowels, remove_spaces, remove_diacritics=True):
    text = str(text)
    '''
    Normalization and cleaning-up text
    '''
    alphabet = None
    vowels = None
    language = language.upper()
    if (language == 'ENGLISH') or (language == 'ENG') or (language == 'EN'):
        alphabet = alphabet_map["ENG"]
        vowels = vowels_map["ENG"]
    elif (language == '1A') or (language == 'SWAHILI') or (language == 'SWA') or (language == 'SW'):
        alphabet = alphabet_map["SWA"]
        vowels = vowels_map["SWA"]
    elif (language == '1B') or (language == 'TAGALOG') or (language == 'TGL') or (language == 'TL'):
        alphabet = alphabet_map["TGL"]
        vowels = vowels_map["TGL"]
    elif (language == '1S') or (language == 'SOMALI') or (language == 'SOM') or (language == 'SO'):
        alphabet = alphabet_map["SOM"]
        vowels = vowels_map["SOM"]
    elif (language == '2B') or (language == 'LITHUANIAN') or (language == 'LIT') or (language == 'LT'):
        alphabet = alphabet_map["LIT"]
        vowels = vowels_map["LIT"]
    else:
        table = str.maketrans({key: None for key in string.punctuation})
        new_s = text.translate(table)
        return new_s
        #return text
        
    lowercase=True
    remove_repetitions_count=0
    if remove_repetitions == True:
        remove_repetitions_count=1

    remove_punct = True
    remove_digits = True
    remove_apostrophe = True
    
    '''Lowercase text, if required'''
    if lowercase == True:
        text = text.lower()
    
    '''Remove repititions of a specific length, if required'''
    if remove_repetitions_count > 0:
        replacement = r''
        for count in range(remove_repetitions_count):
            replacement += '\\1'
        text = re.sub(r'(.)\1{'+str(remove_repetitions_count)+',}', replacement, text)

    '''Remove punctuation marks, if required'''
    if remove_punct == True:
        text = re.sub(r"[^\w\s\']",'', text)
        text = re.sub(r"(^|\s)[\']", r'\1', text) 

    '''Remove digits, if required'''
    if remove_digits == True:
        text = re.sub(r'\d', '', text)

    '''Remove apostrophe, if required'''
    if remove_apostrophe == True:
        text = re.sub(r'([a-zA-Z])[\']', r'\1', text)

    '''Remove spaces, if required.''' 
    if remove_spaces == True:
        text = re.sub(r'\s', '', text)

    '''Loop over the unique characters in the text'''
    for char in list(set(text)):
        if not char.isspace() and not char.isdigit() and not re.match(r"[^\w\s\d]", char):

            '''Remove diacritics, if required.'''
            if remove_diacritics:
                lower = char == char.lower()
                char_norm = char
                if char.lower() in character_mappings:
                    char_norm = character_mappings[char.lower()]
                elif char.lower() not in alphabet:
                    char_norm = unicodedata.normalize('NFD', char)
                    char_norm = char_norm.encode('ascii', 'ignore')
                    char_norm = char_norm.decode("utf-8")
                if not lower:
                    char_norm = char_norm.upper()
                if char != char_norm:
                    text = re.sub(re.escape(char), char_norm, text)
                    char = char_norm

            ''' Remove any character that is not in the alphabet. Also, remove vowels, if required '''
            if (char.lower() in vowels and remove_vowels == True) or char.lower() not in alphabet:
                text = re.sub(re.escape(char), '', text)

    '''Remove extra spaces'''
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
'''
s = str("³")
s = str("5")
print(bytes(s, "utf-8"))
test = normalize("lt", s , False, False, False)
print(bytes(test, "utf-8"))
'''
