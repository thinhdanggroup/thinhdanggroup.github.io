import axios from 'axios'

// import * as actionTypes from './types'
import * as backendInfo from '../backend-info'

export function pingBackendServer(then) {
  axios({
    method: 'get',
    url: `${backendInfo.url}`,
  }).then(then)
}

export function getBaiHatById(idBaiHat, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getBaiHatById('${idBaiHat}')`
    }
  }).then(then)
}

export function getInfoForPersonalPage(email, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getInfoForPersonalPage('${email}')`
    }
  }).then(then)
}

export function deletePlaylist(playlistName, memEmail, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT deletePlaylist('${playlistName}','${memEmail}')`
    }
  }).then(then)
}

export function getInfoForPlaylistPage(name, email, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getInfoForPlaylistPage('${name}','${email}')`
    }
  }).then(then)
}

export function addSongToPlaylist(songId, playlistName, memEmail, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT addSongToPlaylist('${songId}','${playlistName}','${memEmail}')`
    }
  }).then(then)
}

export function deleteSongFromPlaylist(songId, playlistName, memEmail, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT deleteSongFromPlaylist('${songId}','${playlistName}','${memEmail}')`
    }
  }).then(then)
}

export function getAlbumById(idAlbum, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getAlbumById('${idAlbum}')`
    }
  }).then(then)
}

export function postComment(email, noiDung, idBaiHat, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT postComment('${email}','${noiDung}','${idBaiHat}')`
    }
  }).then(then)
}

export function ratingBH(email, idBaiHat, soSao, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT rateBaiHat('${email}','${idBaiHat}','${soSao}')`
    }
  }).then(then)
}

export function getInfoForArtistPage(artistId, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getInfoForArtistPage('${artistId}')`
    }
  }).then(then)
}

export function getMembersEmail(then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getMembersEmail()`
    }
  }).then(then)
}

export function getPlaylistsNameOfAMember(memEmail, then) {
  axios({
    method: 'post',
    url: `${backendInfo.url}/query-db`,
    data: {
      query: `SELECT getPlaylistsNameOfAMember('${memEmail}')`
    }
  }).then(then)
}