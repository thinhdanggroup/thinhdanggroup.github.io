import React, { Component } from 'react';
import stickyOnScroll from '../components/stickyOnScroll';

const defaultProps = {
  playingSongId: null,
  user: null,
};


class WorkInfo extends Component {
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
                  <h2>Work Experience</h2>
                </div>
              </div>
            </div>
            <div className="row">
              <div className="col-md-12">
                <div className="content-item">
                  <small>Jun 2017 - Aug 2017</small>
                  <h3>Penetration tester</h3>
                  <h4><em>Full-time staff</em></h4>
                  <h4>Earst & Young Viet Nam</h4>
                  {/* <p>United Kingdom, London</p> */}
                </div>
                <div className="content-item">
                  <small>Jan 2018 - Present</small>
                  <h3>Software Engineering</h3>
                  <h4><em>Part-time staff</em></h4>
                  <h4>VNG Cooperation</h4>
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

WorkInfo.defaultProps = defaultProps;
// BXH.propTypes = propTypes;

export default stickyOnScroll(WorkInfo, 50);
