import { normalize } from 'normalizr';
import { fetchSongsSuccess } from '../actions/PlaylistActions';
import * as types from '../constants/ActionTypes';
import { songSchema, memberSchema } from '../constants/Schemas';
import { callApi } from '../utils/ApiUtils';


const fetchMemberSuccess = entities => ({
  type: types.FETCH_USER_SUCCESS,
  entities,
});

const fetchMember = (email) => async (dispatch) => {
  let { json } = await callApi(`SELECT getInfoForPersonalPage('${email}')`);
  json = json.data.getinfoforpersonalpage

  dispatch(fetchMemberSuccess({
    members: {
      [email]: json
    }
  }));
};

const fetchMemberIfNeeded = (shouldFetchUser, email) => (dispatch) => {
  if (shouldFetchUser) {
    dispatch(fetchMember(email));
  }
};

export default fetchMemberIfNeeded;
