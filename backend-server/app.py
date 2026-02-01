import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import nltk
from nltk.stem import WordNetLemmatizer
import pickle
import numpy as np
from keras.models import load_model
import json
import random
import requests  

app = Flask(__name__)
CORS(app)

lemmatizer = WordNetLemmatizer()
model = load_model('chatbot_model.h5')
intents = json.loads(open('intents.json').read())
words = pickle.load(open('words.pkl', 'rb'))
classes = pickle.load(open('classes.pkl', 'rb'))

TMDB_API_KEY = "3fd2be6f0c70a2a598f084ddfb75487c"  
TMDB_BASE_URL = "https://api.themoviedb.org/3"

GENRE_MAP = {
    "recommend_action": 28,
    "recommend_comedy": 35,
    "recommend_horror": 27,
    "recommend_scifi": 878,
    "recommend_romance": 10749,
    "recommend_thriller": 53,
    "recommend_animation": 16,
    "family_friendly": 10751
}

def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

def bag_of_words(sentence, words, show_details=True):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for s in sentence_words:
        for i, word in enumerate(words):
            if word == s:
                bag[i] = 1
    return np.array(bag)

def predict_class(sentence):
    p = bag_of_words(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list

def fetch_movies_from_tmdb(genre_id):
    try:
        
        url = f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&with_genres={genre_id}&sort_by=popularity.desc&language=en-US&page=1"
        response = requests.get(url)
        data = response.json()
        
        movies = data.get('results', [])
        if not movies:
            return "I couldn't find any movies for that genre right now."
            
        selected_movies = random.sample(movies, min(3, len(movies)))
        
        reply = "Here are 3 trending suggestions based on live data:<br>"
        for m in selected_movies:
            title = m['title']
            rating = m['vote_average']
            reply += f"🎬 <b>{title}</b> (⭐ {rating}/10)<br>"
            
        return reply

    except Exception as e:
        print(f"API Error: {e}")
        return "Sorry, I'm having trouble connecting to the movie database."

def get_response(ints, intents_json):
    tag = ints[0]['intent']
    
    if tag in GENRE_MAP:
        genre_id = GENRE_MAP[tag]
        return fetch_movies_from_tmdb(genre_id)
    
    elif tag == "trending_movies":
        try:
            url = f"{TMDB_BASE_URL}/trending/movie/week?api_key={TMDB_API_KEY}"
            response = requests.get(url)
            data = response.json()
            movies = data.get('results', [])[:3] 
            reply = "🔥 <b>Trending this week:</b><br>"
            for m in movies:
                reply += f"• {m['title']}<br>"
            return reply
        except:
            return "Could not fetch trending movies."

    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if i['tag'] == tag:
            result = random.choice(i['responses'])
            break
    return result

@app.route('/chat', methods=['POST'])
def chat():
    message = request.json['message']
    ints = predict_class(message)
    response = get_response(ints, intents)
    return jsonify({"response": response})

if __name__ == '__main__':
    # Use the PORT environment variable if available, otherwise 5000
    port = int(os.environ.get("PORT", 5000))
    # Host must be 0.0.0.0 to be accessible on the cloud
    app.run(host='0.0.0.0', port=port)