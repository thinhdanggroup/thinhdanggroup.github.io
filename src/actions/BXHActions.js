import { normalize } from 'normalizr';
import { fetchSongsSuccess } from '../actions/PlaylistActions';
import * as types from '../constants/ActionTypes';
import { songSchema } from '../constants/Schemas';
import { callApi } from '../utils/ApiUtils';


const fetchBXHSuccess = entities => ({
  type: types.FETCH_USER_SUCCESS,
  entities,
});

const fetchBXH = (playlist) => async (dispatch) => {
  let { json } = await callApi(`SELECT getTopBXH(10);`);
  json = json.data.gettopbxh;
  console.log(json);
  // dispatch(fetchBXHSuccess({
  //     songs: {
  //       [id]: json
  //     },
  // // }));
  // dispatch(fetchBXHSuccess({
  //   albums: {
  //     1111111 : json
  //   }
  // }));

  const normSongs = normalize(json.baiHats, [songSchema]);

  dispatch(fetchSongsSuccess(playlist,normSongs.result, normSongs.entities, null, null));
};



const fetchBXHIfNeeded = (shouldFetchUser,playlist) => (dispatch) => {
  if (shouldFetchUser) {
    dispatch(fetchBXH(playlist));
  }
};

export default fetchBXHIfNeeded;
