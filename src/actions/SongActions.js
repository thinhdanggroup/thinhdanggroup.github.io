import { normalize } from 'normalizr';
import { fetchSongs, fetchSongsSuccess } from '../actions/PlaylistActions';
import * as types from '../constants/ActionTypes';
import { QUERY_DB_URL } from '../constants/ApiConstants';
import { songSchema } from '../constants/Schemas';
import { callApi } from '../utils/ApiUtils';

const fetchSong = (id, playlist) => async (dispatch) => {
  let { json } = await callApi(`SELECT getBaiHatById(idbaihat:='${id}')`);
  json = json.data.getbaihatbyid

  const result = id;
  const entities = {
    songs: {
      [id]: json
    },
  }

  dispatch(fetchSongsSuccess(playlist, [result], entities, null, null));
  // dispatch(fetchSongs(playlist, USER_SONGS_URL.replace(':id', userId)));
};

const shouldFetchSong = (id, state) => {
  const { entities } = state;
  const { songs } = entities;
  const songExists = id in songs;
  const songHasComments = songExists ? 'comments' in songs[id] : false;

  return !songExists || !songHasComments;
};

const fetchSongIfNeeded = (id, playlist) => (dispatch, getState) => {
  if (shouldFetchSong(id, getState())) {
    dispatch(fetchSong(id, playlist));
  }
};

export default fetchSongIfNeeded;
