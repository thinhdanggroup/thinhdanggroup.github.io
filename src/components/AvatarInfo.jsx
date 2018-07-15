import React, { Component } from 'react';
import stickyOnScroll from '../components/stickyOnScroll';

const defaultProps = {
  playingSongId: null,
  user: null,
};


class AvatarInfo extends Component {
  componentWillMount() {
  }

  componentWillReceiveProps(nextProps) {
  }

  render() {

    return (
      <div>
        <div className="profile-img">
          <img src={require('../images/avatar.jpg')} className="img-fluid" alt="What the hell" />
        </div>
        <div className="content">
          <h1>Thinh Dang-An</h1>
          <ul class="list-group">
            <span className="spanst-group-item"><small><strong>Software Engineering</strong></small></span>
            <span className="spanst-group-item"><small><strong>Gender</strong>: Male</small></span>
            <span className="spanst-group-item"><small><strong>Phone</strong>: +84971418869</small></span>
            <span className="spanst-group-item"><small><strong>Email</strong>: thinhdang206@gmail.com</small></span>
            <span className="spanst-group-item"><small><strong>Address</strong>: Ho Chi Minh, Vietnam</small></span>
          </ul>

          <div className="about-text">
            <p>
              I want to learn from your company. Besides, I also want to hone my technical skills and communication skills. Especially, I want to know more about your company and contribute to your company's success.
            </p>

            <p>Energistically fabricate customized imperatives through cooperative catalysts for change.</p>


            <p><img src="img/Signature.png" alt="" className="img-responsive" /></p>
          </div>


          <ul className="social-icon">
            <li><a href="https://www.facebook.com/thinh.dang.69"><i className="fa fa-facebook" aria-hidden="true"></i></a></li>
            <li><a href="https://www.linkedin.com/in/thinh-dang/"><i className="fa fa-linkedin" aria-hidden="true"></i></a></li>
            <li><a href="https://github.com/thinhdanggroup"><i className="fa fa-github" aria-hidden="true"></i></a></li>
          </ul>
        </div>
      </div>
    );
  }
}

AvatarInfo.defaultProps = defaultProps;
// BXH.propTypes = propTypes;

export default stickyOnScroll(AvatarInfo, 50);
