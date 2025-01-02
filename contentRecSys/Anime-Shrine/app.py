import numpy as np
import pandas as pd
import random
import string
import re
import math
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

def get_index_from_name(name):
    return df[df['name']==name].index.tolist()[0]
def clean(text):

    # Remove all punctuation:
    for char in text:
        if char in string.punctuation+u'\N{DEGREE SIGN}'+'039':
            text = text.replace(char,"")

    # Convert to lowercase:
    text = re.sub(r'&quot;', '', text)
    text = re.sub(r'.hack//', '', text)
    text = re.sub(r'&#039;', '', text)
    text = re.sub(r'A&#039;s', '', text)
    text = re.sub(r'I&#039;', 'I\'', text)
    text = re.sub(r'&amp;', 'and', text)
    text = re.sub(u'\N{DEGREE SIGN}','',text)
    #text = text.lower()

    return text
def genre_process(data):
  genre = data.genre.to_numpy()
  genre_list = []
  genre_dict = {}

  for g in genre:
    genre_list.extend(g.split(', '))
  genre_list = list(set(genre_list))

  for idx in range(len(genre_list)):
    genre_dict[genre_list[idx]] = idx

  genre_num = len(genre_list)
  movie_num = len(data.index)

  data = np.zeros((movie_num, genre_num))
  for idx in range(len(genre)):
    for g in genre[idx].split(', '):
      data[idx, genre_dict[g]] = 1
  return data
def normalized(data):
  norm_data = []
  val_cal = np.sum(data, axis=1)
  for row in range(data.shape[0]):
    norm_data.append(data[row]/np.sqrt(val_cal[row]))
  return np.array(norm_data)
def idf(data):
  df = np.sum(data, axis=0)
  idf = 1 + np.emath.logn(data.shape[0], 1/df)
  return idf
def profile_cal(data, user_rating):
  user_profile = np.dot(user_rating, data)
  return user_profile
def content_rec(df, rated_filter, user_rating):
  data = genre_process(df)

  norm_data = normalized(data)
  idf_score = idf(data)
  w_data = np.array(norm_data * idf_score)

  user_profile = profile_cal(norm_data, user_rating)
  prediction = np.round(np.dot(w_data, user_profile), 3)
  pred_dict = pd.DataFrame({'anime_id' : df.anime_id[~rated_filter], 'anime_name' : df.name[~rated_filter], 'rating' : df.rating[~rated_filter]}).sort_values(by = ['rating'], ascending = False)
  return pred_dict.head(10).to_numpy()

def interest_eval(type, description):
  if type == 'score':
    return float(description)
  elif type == 'hover':
    return min(9.0, description - 1.0)
  elif type == 'view':
    return max(1.0, round(float(math.floor(description/10)), 3))
  elif type == 'like':
    return 9.0
  elif type == 'dislike':
    return 1.0
  elif type == 'comment':
    return 6.0
  elif type == 'suggest':
    return 9.0
  assert()
  
def rating_cal(activity, static_rating, dynamic_rating):
  new_rating = interest_eval(activity['type'], activity['description'])

  if activity['type'] == 'score':
      static_rating[activity['movie_id']] = new_rating
  else:

    if activity['movie_id'] not in dynamic_rating.keys():
      dynamic_rating[activity['movie_id']] = new_rating
    else:
      if activity['type'] != 'hover' and activity['type'] != 'suggest':
        if new_rating < dynamic_rating[activity['movie_id']]:
          if new_rating <= 5:
            dynamic_rating[activity['movie_id']] = round(0.6 * new_rating + 0.4 * dynamic_rating[activity['movie_id']], 3)
        else:
          dynamic_rating[activity['movie_id']] = new_rating

def user_rating(df, static_rating, dynamic_rating):
  rating = np.zeros(len(df.index))
  for id in dynamic_rating.keys():
    rating[id_to_idx[id]] = dynamic_rating[id]

  for id in static_rating.keys():
    rating[id_to_idx[id]] = static_rating[id]
  return rating

def static_transform(rating, user_id, static_rating):
  user_rating = rating[rating.user_id == user_id].to_numpy()
  for r in user_rating:
    static_rating[r[1]] = r[2]

def popular_retrieve(df):
  rating = df.rating.to_numpy()
  member = df.members.to_numpy()

  r_condition = random.uniform(np.quantile(rating, 0.75), np.quantile(rating, 0.95))
  m_condition = random.uniform(np.quantile(member, 0.75), np.quantile(member, 0.95))

  filter = [value1 and value2 for value1, value2 in zip(rating > r_condition, member > m_condition)]
  return df.to_numpy()[:,[0,1]][filter]

def final_rec(df, history, rating, rate):
  recommendation = []
  rated_filter = rate != 0

  rate_num = rating.user_id.value_counts().to_numpy()
  score_num = len(history)

  popular = popular_retrieve(df)
  popular_num = 0

  content = content_rec(df, rated_filter, rate)[:,[0,1]]
  content_num = 10
  
  if score_num <= np.quantile(rate_num, 0.25):
      content_num = round(score_num*10/np.quantile(rate_num, 0.25))
      popular_num = 10 - content_num
  
  final_content = content[:content_num]
  final_content = [[anime[0], anime[1], 1] for anime in final_content]

  final_popular = []
  movie_num = 0
  while movie_num < popular_num:
    anime = popular[random.randint(0, len(popular) - 1)]
    if anime[1] not in final_content and anime[1] not in df.name[rated_filter].to_numpy():
      final_popular.append(anime)
      movie_num += 1
  final_popular = [[anime[0], anime[1], 0] for anime in final_popular]

  recommendation.extend(final_content)
  recommendation.extend(final_popular)
  
  return recommendation
  
df = pd.read_csv('ML models/data/anime.csv')
df.drop(columns = ['type', 'episodes'], inplace = True)
df.dropna(axis = 0, inplace = True)
df.name = df.name.apply(clean)

rating = pd.read_csv('ML models/data/rating.csv')
rating.replace(-1, np.nan, inplace = True)
rating.dropna(inplace = True)

id_to_idx = {}
for idx, id in enumerate(df['anime_id'].to_numpy()):
  id_to_idx[id] = idx

static_rating = {}
dynamic_rating = {}
id_list = df['anime_id'].to_numpy()
notice = [None]

@app.route('/', methods=['GET', 'POST'])


def index():
    try:
      if request.method =='POST':
          id = request.form.get("id")
          if int(id) not in id_list:
             assert()
          action = request.form.get("action")
          description = request.form.get("description")

          if action not in ['view', 'score', 'hover']:
              description = 0

          activity = {'movie_id' : int(id), 'type' : action, 'description' : int(description)}

          rating_cal(activity, static_rating, dynamic_rating)
      notice[0] = None
    except:
      notice[0] = 'Something went wrong'
    
    anime_name = df['name'].to_numpy()
    history = [[int(key), anime_name[id_to_idx[key]], value] for key, value in static_rating.items()]
    history.extend([[int(key), anime_name[id_to_idx[key]], value] for key, value in dynamic_rating.items()
                    if key not in static_rating.keys()])

    rate = user_rating(df, static_rating, dynamic_rating)
    recommendation = final_rec(df, history, rating, rate)
    return render_template('./index.HTML', warning = notice[0], result = recommendation, result1 = history)

@app.route('/get_history', methods=['GET', 'POST'])

def get_history():
    try:
      if request.method == 'POST':
        user_id = request.form.get("user_id")
      static_transform(rating, int(user_id), static_rating)
    except:
      notice[0] = 'Something went wrong'
    return redirect('/')
    
@app.route('/reset_history', methods=['GET', 'POST'])

def reset_history():
    try:
      static_rating.clear()
      dynamic_rating.clear()
    except:
      notice[0] = 'Something went wrong'
    return redirect('/')

@app.route('/feedback', methods=['GET', 'POST'])

def feedback():
    try:
      return render_template('./feedback.HTML')
    except:
      return redirect('/')

@app.errorhandler(404)

def page_not_found(e):
    return render_template('404.HTML'), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
