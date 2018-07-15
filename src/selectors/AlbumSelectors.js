import { denormalize } from 'normalizr';
import { createSelector } from 'reselect';
import { ALBUM_PLAYLIST_TYPE } from '../constants/PlaylistConstants';
import { songSchema, albumSchema } from '../constants/Schemas';
import { getEntities, getId, getPlaylists, getSessionFollowings } from '../selectors/CommonSelectors';

export const getPlaylist = createSelector(
  getId,
  id => [ALBUM_PLAYLIST_TYPE, id].join('|'),
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

export const getAlbum = createSelector(
  getId,
  getEntities,
  (id, entities) => (id in entities.albums
    ? denormalize(id, albumSchema, entities)
    : null
  ),
);

export const getShouldFetchUser = createSelector(
  getId,
  getEntities,
  (id, entities) => {
    const { albums } = entities;
    const albumExist = id in albums;

    return !albumExist;
  },
);