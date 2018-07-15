import React, { Component } from 'react';
import stickyOnScroll from '../components/stickyOnScroll';
// import { Button } from 'react-bootstrap';
import AvatarInfo from '../components/AvatarInfo';
import WorkInfo from '../components/WorkInfo';
import ActivitiesInfo from '../components/ActivitiesInfo';
import SkillInfo from '../components/SkillInfo';
import EducationInfo from '../components/EducationInfo';
const defaultProps = {
  playingSongId: null,
  user: null,
};


class CVInfo extends Component {
  componentWillMount() {
  }

  componentWillReceiveProps(nextProps) {
  }

  render() {

    return (
      <div id="page-top" data-spy="scroll" data-target=".navbar">
        <div id="main-wrapper">
          {/* <div id="preloader">
            <div id="status">
              <div className="status-mes"></div>
            </div>
          </div> */}

          <div className="columns-block container">
            <div className="left-col-block blocks">
              <header className="header theiaStickySidebar">
                <AvatarInfo />

              </header>
            </div>


            <div className="right-col-block blocks">
              <div className="theiaStickySidebar">
                <WorkInfo />
                <SkillInfo />

                <ActivitiesInfo />
                <EducationInfo />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  } div
}

CVInfo.defaultProps = defaultProps;
// BXH.propTypes = propTypes;

export default stickyOnScroll(CVInfo, 50);
