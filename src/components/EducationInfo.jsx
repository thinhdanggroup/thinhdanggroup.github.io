import React, { Component } from 'react';
import stickyOnScroll from '../components/stickyOnScroll';

const defaultProps = {
  playingSongId: null,
  user: null,
};


class EducationInfo extends Component {
  componentWillMount() {
  }

  componentWillReceiveProps(nextProps) {
  }

  render() {

    return (
      <div>
        <section className="section-wrapper section-experience gray-bg">
          <div className="container-fluid">
            <div className="row">
              <div className="col-md-12">
                <div className="section-title">
                  <h2>Education</h2>
                </div>
              </div>
            </div>
            <div className="row">
              <div className="col-md-12">
                <div className="content-item">
                  <small>Sep 2014 - present</small>
                  <h3>Back Khoa University, Viet Nam</h3>
                  <h4><em>Computer Engineering</em></h4>
                  <h4><strong>GPA</strong>: 8.3/10</h4>
                  {/* <p>United Kingdom, London</p> */}
                </div>
              </div>
            </div>
          </div>

        </section>
      </div>
    );
  }
}

EducationInfo.defaultProps = defaultProps;
// BXH.propTypes = propTypes;

export default stickyOnScroll(EducationInfo, 50);
