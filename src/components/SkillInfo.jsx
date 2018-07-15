import React, { Component } from 'react';
import stickyOnScroll from '../components/stickyOnScroll';

const defaultProps = {
  playingSongId: null,
  user: null,
};


class SkillInfo extends Component {
  componentWillMount() {
  }

  componentWillReceiveProps(nextProps) {
  }

  render() {
    const Clang = {
      width: '80%',
    };
    const Java = {
      width: '60%',
    };
    const Javascript = {
      width: '50%',
    };
    const SQL = {
      width: '70%',
    };
    const Python = {
      width: '80%',
    };
    const Vietnamese = {
      width: '100%',
    };
    return (
      <div>
        <section className="section-wrapper skills-wrapper">
          <div className="container-fluid">
            <div className="row">
              <div className="col-md-12">
                <div className="section-title">
                  <h2>Skills</h2>
                </div>
              </div>

            </div>
            <div className="row">
              <div className="col-md-12">
                <div className="progress-wrapper">

                  <div className="row">
                    <div class="col-sm-4"><p><u>Languages</u></p></div>
                    <div class="col-sm-8">
                      <a> English,Vietnamese </a>
                    </div>

                  </div>
                  <div className="row">
                    <div className="col-sm-2" />
                    <div className="col-sm-10" >
                      <div className="progress-item">
                        <span className="progress-title">English</span>

                        <div className="progress">
                          <div className="progress-bar" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={SQL}>
                            <span className="progress-percent"> 70%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-sm-2" />
                    <div className="col-sm-10" >
                      <div className="progress-item">
                        <span className="progress-title">Vietnamese</span>

                        <div className="progress">
                          <div className="progress-bar" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={Vietnamese}>
                            <span className="progress-percent"> 100%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <p />
                  <div className="row">
                    <div class="col-sm-4"><p><u><strong>Report</strong></u></p></div>
                    <div class="col-sm-8">
                      <a>Word, Latex</a>
                    </div>

                  </div>
                  <div className="row">
                    <div class="col-sm-4"><p><u><strong>Programing Languages</strong></u></p></div>
                    <div class="col-sm-8">
                      <a>Python, C, C++, C#, Javascript, SQL, Java</a>
                    </div>

                  </div>
                  <div className="row">
                    <div className="col-sm-2" />
                    <div className="col-sm-10" >
                      <div className="progress-item">
                        <span className="progress-title">C Languages</span>

                        <div className="progress">
                          <div className="progress-bar" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={Clang}>
                            <span className="progress-percent"> 80%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-sm-2" />
                    <div className="col-sm-10" >
                      <div className="progress-item">
                        <span className="progress-title">Java</span>

                        <div className="progress">
                          <div className="progress-bar" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={Java}>
                            <span className="progress-percent"> 60%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-sm-2" />
                    <div className="col-sm-10" >
                      <div className="progress-item">
                        <span className="progress-title">Javascript</span>

                        <div className="progress">
                          <div className="progress-bar" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={Javascript}>
                            <span className="progress-percent"> 50%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-sm-2" />
                    <div className="col-sm-10" >
                      <div className="progress-item">
                        <span className="progress-title">SQL</span>

                        <div className="progress">
                          <div className="progress-bar" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={SQL}>
                            <span className="progress-percent"> 70%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="row">
                    <div className="col-sm-2" />
                    <div className="col-sm-10" >
                      <div className="progress-item">
                        <span className="progress-title">Python</span>

                        <div className="progress">
                          <div className="progress-bar" role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100" style={Python}>
                            <span className="progress-percent"> 80%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <p />
                  <div className="row">
                    <div class="col-sm-4"><p><u><strong>Experiences</strong></u></p></div>
                    <div class="col-sm-8">
                      <a>Framework(React.js, Redux), Design Pattern</a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div >
    );
  }
}

SkillInfo.defaultProps = defaultProps;
// BXH.propTypes = propTypes;

export default stickyOnScroll(SkillInfo, 50);
