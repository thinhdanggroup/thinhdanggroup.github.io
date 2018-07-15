import React, { Component } from 'react';
import { Provider } from 'react-redux'
import 'bootstrap/dist/css/bootstrap.css';
import RootContainer from './containers/RootContainer';
import configureStore from './store/configureStore';
import './css/style.css';
import './css/font-awesome.min.css';

export default class App extends Component {
  render() {
    return (
      <Provider store={configureStore()}>
        <RootContainer />
      </Provider>
    )
  }
}