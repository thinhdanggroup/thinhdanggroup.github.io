import React from 'react';
import { connect } from 'react-redux';

import { initEnvironment } from '../actions/EnvironmentActions';
import { initRouter } from '../actions/RouterActions';
// import { initAuth } from '../actions/SessionActions';
import Root from '../components/Root';
// import SongsContainer from '../containers/SongsContainer';
import {
  INDEX_PATH,
  CV_PATH,
} from '../constants/RouterConstants';
import CVContainer from './CVContainer';

const RootContainer = props => <Root {...props} />;

const mapStateToProps = (state) => {
  const { router } = state;

  return {
    paths: [
      INDEX_PATH,
      CV_PATH
    ],
    router,
    routes: {
      [INDEX_PATH]: CVContainer,
    },
  };
};

const initAuth = () => { }
export default connect(mapStateToProps, {
  initAuth,
  initEnvironment,
  initRouter,
})(RootContainer);
