import { normalize } from 'normalizr';
import { fetchSongsSuccess } from '../actions/PlaylistActions';
import * as types from '../constants/ActionTypes';
import { songSchema } from '../constants/Schemas';
import { callApi } from '../utils/ApiUtils';

// const fetchUserFollowingsSuccess = entities => ({
//   type: types.FETCH_USER_FOLLOWINGS_SUCCESS,
//   entities,
// });

// const fetchUserFollowings = id => async (dispatch) => {
//   const { json } = await callApi();
//   const { collection } = json;
//   const { entities, result } = normalize(collection, [userSchema]);

//   dispatch(fetchUserFollowingsSuccess({
//     users: {
//       ...entities.users,
//       [id]: { followings: result },
//     },
//   }));
// };

const fetchUserProfilesSuccess = (id, profiles) => ({
  type: types.FETCH_USER_PROFILES_SUCCESS,
  entities: {
    musicians: {
      [id]: { profiles },
    },
  },
});

const fetchUserProfiles = id => async (dispatch) => {
  const { json } = await callApi();
  dispatch(fetchUserProfilesSuccess(id, json.slice(0, 6)));
};

const fetchMusicianSuccess = entities => ({
  type: types.FETCH_USER_SUCCESS,
  entities,
});

const fetchMusician = (id, playlist) => async (dispatch) => {
  let { json } = await callApi(`SELECT getInfoForArtistPage(artistId := '${id}')`);
  json = json.data.getinfoforartistpage

  dispatch(fetchMusicianSuccess({
    musicians: {
      [id]: json
    }
  }));

  const normSongs = normalize(json.artistSongs, [songSchema]);

  dispatch(fetchSongsSuccess(playlist, normSongs.result, normSongs.entities, null, null));
  // dispatch(fetchUserFollowings(id));
  // dispatch(fetchUserProfiles(id));
};

const fetchMusicianIfNeeded = (shouldFetchUser, id, playlist) => (dispatch) => {
  if (shouldFetchUser) {
    dispatch(fetchMusician(id, playlist));
  }
};

export default fetchMusicianIfNeeded;
