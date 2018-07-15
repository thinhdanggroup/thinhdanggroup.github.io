import React, { Component } from 'react';
import stickyOnScroll from '../components/stickyOnScroll';

const defaultProps = {
  playingSongId: null,
  user: null,
};


class ActivitiesInfo extends Component {
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
                  <h2>Activities</h2>
                </div>
              </div>
            </div>
            <div className="row">
              <div className="col-md-12">
                <div className="content-item">
                  <small>Dec 2016 - Jan 2016</small>
                  <a href="https://bitbucket.org/AThinh/opencv_cuocduaso/overview"><h3>"Run the Race" Challenge</h3></a>
                  <dl>
                    <dd>- Working with OpenCV and CUDA</dd>
                    <dd>- Know how to detect things in videos</dd>
                  </dl>
                </div>
                <div className="content-item">
                  <small>Dec 2016 - Dec 2017</small>
                  <a href="https://github.com/CEOutlaws/Kaithy_Reboot"><h3>"Developing Artificial Intelligence to play Gomoku by applying Q-Learning" research</h3></a>
                  <dl>
                    <dd>- Understand about AI( machine learning and deep learning)</dd>
                    <dd>- Improve programing skill when I work with Tensorflow</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

        </section>
      </div>
    );
  }
}

ActivitiesInfo.defaultProps = defaultProps;
// BXH.propTypes = propTypes;

export default stickyOnScroll(ActivitiesInfo, 50);
