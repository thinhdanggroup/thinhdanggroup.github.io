import { denormalize } from 'normalizr';
import { createSelector } from 'reselect';
import { ALBUM_PLAYLIST_TYPE } from '../constants/PlaylistConstants';
import { songSchema, albumSchema, memberSchema } from '../constants/Schemas';
import { getEntities, getPlaylists, getSessionFollowings } from '../selectors/CommonSelectors';

export const getId = state => state.router.route.keys.email;

export const getMember = createSelector(
  getId,
  getEntities,
  (id, entities) => (id in entities.members
    ? denormalize(id, memberSchema, entities)
    : null
  ),
);

export const getShouldFetchMember = createSelector(
  getId,
  getEntities,
  (id, entities) => {
    const { members } = entities;
    const memberExist = id in members;

    return !memberExist;
  },
);