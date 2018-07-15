import * as types from '../constants/ActionTypes';
import { callApi } from '../utils/ApiUtils';
import axios from 'axios'
import * as backendInfo from '../redux/backend-info'
const ratingBHSuccess = (id, avgRate) => ({
  type: types.FETCH_SONG_COMMENTS_SUCCESS,
  entities: {
    songs: {
      [id]: { avgRate },
    },
  },
});
const ratingBHrequest = (email, id, rate) => async (dispatch) => {
  let { json } = await callApi(`SELECT rateBaiHat('${email}','${id}','${rate}');`);
  json = json.data.ratebaihat;
  // console.log(json);
  // dispatch(RatingBHSuccess(id,rate));
};

export const rateSong = (email, id, rate) => (dispatch) => {
  dispatch(ratingBHrequest(email, id, rate));
};


// const fetchRateBHSuccess = (id, rateUser) => ({
//   type: types.FETCH_SONG_COMMENTS_SUCCESS,
//   entities: {
//     songs: {
//       [id]: { rateUser },
//     },
//   },
// });
// const fetchRateBHrequest = (id,email) => async (dispatch) => {
//   let { json } = await callApi(`SELECT getRateUser('${email}','${id}');`);
//   dispatch(fetchRateBHSuccess(id,json.data.rate));
// }
// export const fetchRateBH= (id,email) => (dispatch) => {
//   dispatch(fetchRateBHrequest(id,email));
// }
export function fetchRateBH(id, email, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getRateUser('${email}','${id}');`
    }
  }).then(then)
}