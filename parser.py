#!/usr/bin/python

import nltk
import os
nltk.data.path.append(os.getcwd() + '/dataset/')
from nltk.corpus import semcor

from gensim.models import Word2Vec

from extractor import *
from misc import *

def scan_corpus(index_file, f_parse):
    tag_files = load_tag_fies(index_file)
    for filename in tag_files:
        print 'parsing %s...' % filename
        sentences = semcor.xml(filename).findall('context/p/s')
        f_parse(sentences)

class ModelTrainer:
    def __init__(self):
        self._model = Word2Vec(size=100, window=5, min_count=5, workers=2)
        self._trained = False
    def parse(self, sentences):
        sent_str = map(lambda x:self.__semcor_sent2str(x), sentences)
        if not self._trained:
            self.model.build_vocab(sent_str)
            self._trained = True
        else:
            self.model.build_vocab(sent_str,update=True)
        self.model.train(sent_str,total_examples=self.model.corpus_count,epochs=self.model.iter)

    @staticmethod
    def __semcor_sent2str(sent):
        return map(lambda x: x.text, sent);

    @property
    def model(self):
        return self._model

class WordStat:
    def __init__(self, init_map={}):
        self.senses = init_map
    def update(self, x):
        if x == None: return
        if not x.isdigit(): return

        if x not in self.senses.keys():
            self.senses[x] = 0
        self.senses[x] += 1
    def dump(self):
        for k,v in self.senses.items():
            print k,v
    def keys(self):
        return self.senses.keys()
    def items(self):
        return self.senses.items()

class CorpusParser:
    def __init__(self, index_file, force_update=False):
        # try to load from pickle file first
        pkl_dir = './pickle'
        pkl_file = '%s/%s_word_map.pkl' % (pkl_dir,
                os.path.basename(index_file).split('.')[0])
        loaded = load(pkl_file)

        if loaded != None and force_update==False:
            self.word_map = loaded
        else:
            self.word_map = {}
            # have to parse corpose
            tag_files = load_tag_fies(index_file)
            for f in tag_files:
                self.parse(f)

            if not os.path.exists(pkl_dir):
                os.makedirs(pkl_dir)

            save(self.word_map, pkl_file)

    def parse(self,filename):
        # get sentence from semcor file
        print 'parsing %s...' % filename
        sentences = semcor.xml(filename).findall('context/p/s')

        for sent in sentences:
            for wordform in sent.getchildren():
                lemma = wordform.get('lemma')
                sense_id = wordform.get('wnsn')

                if lemma not in self.word_map.keys():
                    self.word_map[lemma] = WordStat()
                self.word_map[lemma].update(sense_id)

def filter_word_map(word_map, min_sense_appr):
    filtered_map = {}
    for word, senses in word_map.items():
        dense_senses = {}
        for sid, count in senses.items():
            if count > min_sense_appr:
                dense_senses[sid] = count
        if len(dense_senses.keys()) > 1: 
            filtered_map[word] = WordStat(dense_senses)
        else:
            print sid, count
    return filtered_map

def load_word2vec_model(index_file, force_update=False):
    model_dir = 'model'
    model_file = './%s/%s_w2v.embedding' % (model_dir, 
                os.path.basename(index_file).split('.')[0])

    if os.path.isfile(model_file) and not force_update:
        print 'Load from %s' % model_file
        model = Word2Vec.load(model_file)
    else:
        trainer = ModelTrainer()
        scan_corpus(index_file, trainer.parse)
        model = trainer.model
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        model.save(model_file)
        print 'Saved model to %s' % model_file
    return model

if __name__ == '__main__':
    index_file = './dataset/semcor_tagfiles_full.txt'
    # index_file = './dataset/brown1_tagfiles.txt'
    
    word2vec_model = load_word2vec_model(index_file, force_update=False)

    word_map = CorpusParser(index_file,force_update=False).word_map

    MIN_SENSE_APPR = 1000
    ambiguous_words = filter_word_map(word_map, MIN_SENSE_APPR)
    # print '%d ambiguous words' % len(ambiguous_words.keys())

    ce = ContextExtractor(ambiguous_words, word2vec_model)
    ce.go(index_file)
    ce.dump2file()
    # ce.dump()
