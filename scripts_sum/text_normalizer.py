'''
Created on Jul 24, 2018
Updated on Oct 23, 2018
Modified on Sep 23, 2019
Modified on Sep 24, 2019

@author: ezotkina
@author: reskander
@author: srnair
'''
# coding=utf-8
# -*- coding: utf-8 -*-

import sys
import re
import unicodedata
import string
from mosestokenizer import *

class TextNormalizer:
    
    def __init__(self,language):
        self.language = language
        english_alphabet = "abcdefghijklmnopqrstuvwxyz"
        english_vowels = "aeiou"

        swahili_alphabet = "abcdefghijklmnopqrstuvwxyz"
        swahili_vowels = "aeiou"

        tagalog_alphabet = "abcdefghijklmnopqrstuvwxyz"
        tagalog_vowels = "aeiou"

        somali_alphabet = "abcdefghijklmnopqrstuvwxyz"
        somali_vowels = "aeiou"

        lithuanian_alphabet = "aąbcčdeęėfghiįyjklmnoprsštuųūvzž"
        lithuanian_vowels = "aąeęėiįouųū"

        bulgarian_alphabet = "абвгдежзийклмнопрстуфхцчшщъьюя"
        bulgarian_vowels = "аеиоуъ"

        self.alphabet_map = {}
        self.alphabet_map["ENG"] = english_alphabet;
        self.alphabet_map["TGL"] = tagalog_alphabet;
        self.alphabet_map["SWA"] = swahili_alphabet;
        self.alphabet_map["SOM"] = somali_alphabet;
        self.alphabet_map["LIT"] = lithuanian_alphabet;
        self.alphabet_map["BUL"] = bulgarian_alphabet;
        
        self.vowels_map = {}
        self.vowels_map["ENG"] = english_vowels;
        self.vowels_map["TGL"] = tagalog_vowels;
        self.vowels_map["SWA"] = swahili_vowels;
        self.vowels_map["SOM"] = somali_vowels;
        self.vowels_map["LIT"] = lithuanian_vowels;
        self.vowels_map["BUL"] = bulgarian_vowels;

        ''' Special cxases not handled by the default unicode undiacritization '''
        self.character_mappings = {
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
        self.tokenize = MosesTokenizer(language)
        self.norm = MosesPunctuationNormalizer(language)

    def normalize(self, text, remove_repetitions, remove_vowels, remove_spaces, remove_diacritics=True):
        remove_repetitions_count = 0
        if remove_repetitions == True:
            remove_repetitions_count = 1
            
        return self.normalize_full(text, "", "", True, remove_repetitions_count, True, True, remove_vowels, remove_diacritics, remove_spaces, True)
        
    def normalize_full(self, text, letters_to_keep, letters_to_remove, lowercase, remove_repetitions_count, remove_punct, remove_digits, remove_vowels, remove_diacritics, remove_spaces, remove_apostrophe):
        '''
        Normalization and cleaning-up text
        '''
        if text: text = " ".join(self.tokenize(self.norm(text)))
        
        alphabet = None
        vowels = None
        language = self.language.upper()
        if (language == 'ENGLISH') or (language == 'ENG') or (language == 'EN'):
            alphabet = self.alphabet_map["ENG"]
            vowels = self.vowels_map["ENG"]
        elif (language == '1A') or (language == 'SWAHILI') or (language == 'SWA') or (language == 'SW'):
            alphabet = self.alphabet_map["SWA"]
            vowels = self.vowels_map["SWA"]
        elif (language == '1B') or (language == 'TAGALOG') or (language == 'TGL') or (language == 'TL'):
            alphabet = self.alphabet_map["TGL"]
            vowels = self.vowels_map["TGL"]
        elif (language == '1S') or (language == 'SOMALI') or (language == 'SOM') or (language == 'SO'):
            alphabet = self.alphabet_map["SOM"]
            vowels = self.vowels_map["SOM"]
        elif (language == '2B') or (language == 'LITHUANIAN') or (language == 'LIT') or (language == 'LT'):
            alphabet = self.alphabet_map["LIT"]
            vowels = self.vowels_map["LIT"]
        elif (language == '2S') or (language == 'BULGARIAN') or (language == 'BUL') or (language == 'BG'):
            alphabet = self.alphabet_map["BUL"]
            vowels = self.vowels_map["BUL"]
        else:
            table = str.maketrans({key: None for key in string.punctuation})
            new_s = text.translate(table)
            return new_s
        
        '''Prepare the lists of the letters to be explictily kept and removed'''
        letters_in = list(letters_to_keep)
        letters_out = list(letters_to_remove)
        
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
            text = re.sub(r'\'', '', text)
    
        '''Remove spaces, if required.''' 
        if remove_spaces == True:
            text = re.sub(r'\s', '', text)
    
        '''Loop over the unique characters in the text'''
        for char in list(set(text)):
            if not char.isspace() and not char.isdigit() and not re.match(r"[^\w\s\d]", char):
    
                '''If the character is needed to be removed, remove it'''
                if char in letters_out:
                    text = re.sub(re.escape(char), '', text)
                    continue
            
                '''Remove diacritics, if required.'''
                if char not in letters_in and remove_diacritics:
                    lower = char == char.lower()
                    char_norm = char
                    if char.lower() in self.character_mappings:
                        char_norm = self.character_mappings[char.lower()]
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
                if char not in letters_in and (char in letters_out or (char.lower() in vowels and remove_vowels == True) or char.lower() not in alphabet):
                    text = re.sub(re.escape(char), '', text)
    
        '''Remove extra spaces'''
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
            

if __name__=="__main__":
    lang = sys.argv[1]
    cleaning = Cleaning(lang)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        print(cleaning.normalize(line, False, False, False))
'''
s = str("³")
s = str("5")
print(bytes(s, "utf-8"))
test = normalize("lt", s , False, False, False)
print(bytes(test, "utf-8"))
#ą č ę ė į š ų ū ž
test = normalize("lt", "ą č ę ė į š ų ū ž", False, False, False)
print(test)
test = normalize("lt", "aąbcčdeęėfghiįyjklmnoprsštuųūvzž", False, False, False)
print(test)
'''
#test = normalize("lt", "vaistai vaistas", True, False, False)
#print(test)
