# -*- coding: utf-8 -*-
"""demo_eval.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1CKyZwSTIYAvnlwczUOh58ZfUPqTD9BSe

# **Loading the data**
"""

import sys
import pandas as pd
import numpy as np
import tensorflow as tf
import ast
path = '/content/drive/MyDrive/Assignment 2/'

data = pd.read_csv('/content/drive/MyDrive/Assignment 2/train.csv')
data['sourceLineTokens'] = data['sourceLineTokens'].apply(ast.literal_eval)
data['targetLineTokens'] = data['targetLineTokens'].apply(ast.literal_eval)

"""# **Constructing a vocabulary**"""

class Vocabulary:
    PAD_token = 0   # Used for padding short sentences
    SOS_token = 1   # Start-of-sentence token
    EOS_token = 2   # End-of-sentence token
    OOV_token = 2   # Out-of-Vocabulary token

    def __init__(self, name=""):
        self.name = name
        self.word2index = {}
        self.word2count = {}
        self.index2word = {Vocabulary.PAD_token: "PAD_Token", Vocabulary.SOS_token: "SOS_Token", Vocabulary.EOS_token: "EOS_Token", Vocabulary.OOV_token: "OOV_Token"}
        self.num_words = 4
        self.num_sentences = 0
        self.longest_sentence = 0

    def add_word(self, word):
        if word not in self.word2index:
            # First entry of word into vocabulary
            self.word2index[word] = self.num_words
            self.word2count[word] = 1
            self.index2word[self.num_words] = word
            self.num_words += 1
        else:
            # Word exists; increase word count
            self.word2count[word] += 1
            
    def add_sentence(self, sentence):
        sentence_len = 0
        for word in sentence:
            sentence_len += 1
            self.add_word(word)
        if sentence_len > self.longest_sentence:
            # This is the longest sentence
            self.longest_sentence = sentence_len
        # Count the number of sentences
        self.num_sentences += 1

    def to_word(self, index):
        return self.index2word[index]

    def to_index(self, word):
        return self.word2index[word]

sourceLineTokensList = []

for i in range(len(data)):
  sourceLineTokensList += data['sourceLineTokens'][i]

o = Vocabulary()
o.add_sentence(sourceLineTokensList)
data_vocabulary = o.word2count

"""# **Extracting the TOP-k tokens into the dictionary**"""

import operator
import itertools
sorted_dict = dict(sorted(data_vocabulary.items(), key=operator.itemgetter(1), reverse=True))
top_k = 500
top_k_dict = dict(itertools.islice(sorted_dict.items(), top_k))
top_k_dict['PAD_Token'] = 0
top_k_dict['SOS_Token'] = 0
top_k_dict['EOS_Token'] = 0
top_k_dict['OOV_Token'] = 0

"""# **Creating the vocabulary for indices**"""

index_dict = {'PAD_Token':0,'SOS_Token':1,'EOS_Token':2,'OOV_Token':3}
j=4
for i in sorted_dict:
  index_dict[i] = j
  j+=1

"""# **Creating the one-hot vector embedding**"""

vector_embedding = np.zeros((len(sorted_dict)+4 , len(top_k_dict)), dtype="int8")
for k,v in index_dict.items():
  if k in top_k_dict:
    vector_embedding[v][v]=1
  else:
    vector_embedding[v][index_dict['OOV_Token']] = 1

"""# **Running the inference**"""

# Define sampling models
# Restore the model and construct the encoder and decoder.
import keras

batch_size = 64
epochs = 100
latent_dim = 256
unique_tokens = len(top_k_dict)
max_length = 50

model = keras.models.load_model('/content/drive/MyDrive/Assignment 2/LSTM_Model')

encoder_inputs = model.input[0]  # input_1
encoder_outputs, state_h_enc, state_c_enc = model.layers[2].output  # lstm_1
encoder_states = [state_h_enc, state_c_enc]
encoder_model = keras.Model(encoder_inputs, encoder_states)

decoder_inputs = model.input[1]  # input_2
decoder_state_input_h = keras.Input(shape=(latent_dim,),name="input_8")
decoder_state_input_c = keras.Input(shape=(latent_dim,),name="input_9")
decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]
decoder_lstm = model.layers[3]
decoder_outputs, state_h_dec, state_c_dec = decoder_lstm(
    decoder_inputs, initial_state=decoder_states_inputs
)
decoder_states = [state_h_dec, state_c_dec]
decoder_dense = model.layers[4]
decoder_outputs = decoder_dense(decoder_outputs)
decoder_model = keras.Model(
    [decoder_inputs] + decoder_states_inputs, [decoder_outputs] + decoder_states
)

# Reverse-lookup token index to decode sequences back to
# something readable.
reverse_input_token_index = dict((i, token) for token, i in index_dict.items())
reverse_target_token_index = dict((i, token) for token, i in index_dict.items())


def decode_sequence(input_seq):
    # Encode the input as state vectors.
    states_value = encoder_model.predict(input_seq)

    # Generate empty target sequence of length 1.
    target_seq = np.zeros((1, 1, unique_tokens))
    # Populate the first token of target sequence with the start token.
    target_seq[0, 0, index_dict['SOS_Token']] = 1.0

    # Sampling loop for a batch of sequences
    # (to simplify, here we assume a batch of size 1).
    stop_condition = False
    # decoded_sentence = ""
    decoded_sentence = []
    while not stop_condition:
        output_tokens, h, c = decoder_model.predict([target_seq] + states_value)

        # Sample a token
        sampled_token_index = np.argmax(output_tokens[0, -1, :])
        sampled_token = reverse_target_token_index[sampled_token_index]
        # decoded_sentence += sampled_token
        #if sampled_token != 'EOS':
        decoded_sentence.append(sampled_token)

        # Exit condition: either hit max length
        # or find stop token.
        if sampled_token == 'EOS_Token' or len(decoded_sentence) >= max_length - 1:  # previously > max_length
            stop_condition = True

        # Update the target sequence (of length 1).
        target_seq = np.zeros((1, 1, unique_tokens))
        target_seq[0, 0, sampled_token_index] = 1.0

        # Update states
        states_value = [h, c]
    return decoded_sentence

"""# **Loading and Preprocessing of test DATA**"""

test_data = pd.read_csv(path+sys.argv[1])

test_data['sourceLineTokens'] = test_data['sourceLineTokens'].apply(ast.literal_eval)
test_data['targetLineTokens'] = test_data['targetLineTokens'].apply(ast.literal_eval)

test_input_text = test_data['sourceLineTokens']
test_output_text = test_data['targetLineTokens']

for i in range(len(test_input_text)):
  if max_length <= len(test_input_text[i]):
    test_input_text[i] = test_input_text[i][0:max_length - 1]
  test_input_text[i].append('EOS_Token')

  if max_length <= len(test_output_text[i]):
    test_output_text[i] = test_output_text[i][0:max_length -2]
  test_output_text[i].append('EOS_Token')

#Inserting the 'OOV_Token' in the output text for matching it with decoded sentence
for i in range(len(test_output_text)):
  for j in range(len(test_output_text[i])):
    if test_output_text[i][j] not in top_k_dict:
      test_output_text[i][j] = 'OOV_Token'

"""# **Creating the test_encoder_input_data**"""

test_encoder_input_data = []

for i in range(len(test_input_text)):
  temp1 = []
  count = 0
  for j in test_input_text[i]:
    if j in top_k_dict:
      temp1.append(vector_embedding[index_dict[j]])
    else:
      j='OOV_Token'
      temp1.append(vector_embedding[index_dict['OOV_Token']])
    count+=1
    if j=='EOS_Token' or count >= max_length:
      break
  while max_length - count != 0 :
    temp1.append(vector_embedding[index_dict['PAD_Token']])
    count+=1
  test_encoder_input_data.append(temp1)

test_encoder_input_data = np.array(test_encoder_input_data)

"""# **Predicting the correct token sequence**

"""

print("RUNNING THE PREDICTION PART")
prediction = []
for seq_index in range(len(test_output_text)):
    # Take one sequence (part of the training set)
    # for trying out decoding.
    input_seq = test_encoder_input_data[seq_index : seq_index + 1]
    decoded_sentence = decode_sequence(input_seq)
    prediction.append(decoded_sentence)

"""# **Generating the output-csv file**"""

valid_out = pd.read_csv(path+sys.argv[1])
valid = []
for i in prediction:
  if 'EOS_Token' in i:
    i.remove('EOS_Token')
  valid.append(str(i))

valid_out['fixedTokens'] = valid
valid_out.to_csv(path+sys.argv[2])