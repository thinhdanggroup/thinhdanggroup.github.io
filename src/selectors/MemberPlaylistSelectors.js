import { denormalize } from 'normalizr';
import { createSelector } from 'reselect';
import { ALBUM_PLAYLIST_TYPE } from '../constants/PlaylistConstants';
import { songSchema, memPlaylistSchema } from '../constants/Schemas';
import { getEntities, getPlaylists, getSessionFollowings } from '../selectors/CommonSelectors';

export const getId = state => [state.router.route.keys.email, state.router.route.keys.playlistName].join('|');

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

export const getMemberPlaylist = createSelector(
  getId,
  getEntities,
  (id, entities) => (id in entities.memPlaylists
    ? denormalize(id, memPlaylistSchema, entities)
    : null
  ),
);

export const getShouldFetchUser = createSelector(
  getId,
  getEntities,
  (id, entities) => {
    const { memPlaylists } = entities;
    const memPlaylistExist = id in memPlaylists;

    return !memPlaylistExist;
  },
);