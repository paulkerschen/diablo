module.exports = {
  publicPath: process.env.NODE_ENV === 'production' ? '/static' : '/',
  lintOnSave: true,
  transpileDependencies: [
    'vuetify'
  ]
}
