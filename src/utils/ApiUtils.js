import camelize from 'camelize'

import { QUERY_DB_URL } from '../constants/ApiConstants';


export const callApi = (query) =>
  fetch(QUERY_DB_URL, {
    method: "POST",
    headers: {
      'Accept': 'application/json, text/plain, */*',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query: query })
  })
    .then(
      response => (response.ok
        ? response.json()
        : Promise.reject(response.text())
      ),
      error => Promise.reject(error))
    .then(
      json => ({ json: camelize(json) }),
      error => ({ error }))
    .catch(error => ({ error }));


