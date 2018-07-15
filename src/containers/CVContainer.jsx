import React from 'react';
import { connect } from 'react-redux';
import CVInfo from '../components/CVInfo';
import { navigateTo } from '../actions/RouterActions';

const CVContainer = props => <CVInfo {...props} />;

const mapStateToProps = (state) => {
  // const { } = state;

  return {
  };
};

const playSong = () => { }
const login = () => { }
const toggleFollow = () => { }
const toggleLike = () => { }

export default connect(mapStateToProps, {
  login,
  toggleFollow,
  toggleLike,
  navigateTo,
  playSong,
})(CVContainer);
