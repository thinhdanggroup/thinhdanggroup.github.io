import { combineReducers, createStore, compose, applyMiddleware } from 'redux'
import ReduxPromise from 'redux-promise'

import * as mainPage from './main-page'

// eslint-disable-next-line
const rootReducers = combineReducers({
  mainPage: mainPage.reducer
})

export const store = createStore(
  rootReducers,
  compose(
    applyMiddleware(ReduxPromise)
  )
)

export const actions = mainPage.actions