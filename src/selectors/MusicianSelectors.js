import { denormalize } from 'normalizr';
import { createSelector } from 'reselect';
import { MUSICIAN_PLAYLIST_TYPE } from '../constants/PlaylistConstants';
import { songSchema, musicianSchema } from '../constants/Schemas';
import { getEntities, getId, getPlaylists, getSessionFollowings } from '../selectors/CommonSelectors';

export const getPlaylist = createSelector(
  getId,
  id => [MUSICIAN_PLAYLIST_TYPE, id].join('|'),
);

export const getSongs = createSelector(
  getPlaylist,
  getPlaylists,
  getEntities,
  (playlist, playlists, entities) => (playlist in playlists
    ? denormalize(playlists[playlist].items, [songSchema], entities)
    : []
  ),
);

export const getUser = createSelector(
  getId,
  getEntities,
  (id, entities) => (id in entities.users
    ? denormalize(id, musicianSchema, entities)
    : null
  ),
);

export const getMusician = createSelector(
  getId,
  getEntities,
  (id, entities) => (id in entities.musicians
    ? denormalize(id, musicianSchema, entities)
    : null
  ),
);

export const getFollowings = createSelector(
  getUser,
  getEntities,
  (user, entities) => (user && user.followings
    ? denormalize(user.followings, [musicianSchema], entities)
    : []
  ),
);

export const getIsFollowing = createSelector(
  getId,
  getSessionFollowings,
  (id, followings) => Boolean(id in followings && followings[id]),
);

export const getShouldFetchUser = createSelector(
  getId,
  getEntities,
  (id, entities) => {
    const { musicians } = entities;
    const musicianExist = id in musicians;
    const musicianHasProfiles = musicianExist ? 'profiles' in musicians[id] : false;

    // return !userExists || !userHasProfiles;
    return !musicianExist;
  },
);

export const getProfiles = createSelector(
  // getUser,
  getMusician,
  user => (user && user.profiles ? user.profiles : []),
);
