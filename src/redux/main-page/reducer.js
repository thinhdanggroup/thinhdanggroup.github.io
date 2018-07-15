import { combineReducers } from 'redux'

import * as actionTypes from './types'
import * as Helper from '../../helper'

function pingBackendServerReducer(state = null, action) {
  switch (action.type) {
    case actionTypes.PING_BACKEND_SERVER:
      if (action.payload.data) {
        return action.payload.data
      }
      else {
        return null
      }
    default:
      return state
  }
}

function loadWeatherReducer(state = {}, action) {
  switch (action.type) {
    case actionTypes.LOAD_WEATHER:
      if (action.payload.data) {
        action.payload.data.data.dateCreated = Helper.parseDates(action.payload.data.data.dateCreated)
        return action.payload.data.data
      }
      else {
        return state
      }
    default:
      return state
  }
}

function loadRealTimeReducer(state = {}, action) {
  switch (action.type) {
    case actionTypes.LOAD_REAL_TIME_WEATHER:
      if (action.payload.data) {
        action.payload.data.data.date = Helper.parseDates(action.payload.data.data.date)
        return action.payload.data.data
      }
      else {
        return state
      }
    default:
      return state
  }
}

function loadForecastReducer(state = {}, action) {
  switch (action.type) {
    case actionTypes.LOAD_FORECAST:
      if (action.payload.data) {
        action.payload.data.data.dateOn.forEach(function (element, index) {
          action.payload.data.data.dateOn[index] = element * 1000
        }, this)
        return action.payload.data.data
      }
      else {
        return state
      }
    default:
      return state
  }
}

const reducer = combineReducers({
  pingResponse: pingBackendServerReducer,
  loadedWeather: loadWeatherReducer,
  loadedRealTimeWeather: loadRealTimeReducer,
  loadedForecast: loadForecastReducer
})

export default reducer;