var webpack = require('webpack');
const path = require('path');

module.exports = {
  mode: 'development',  
  entry: './index.js',
  output: {
    filename: 'main.js',
    path: path.resolve(__dirname, 'shared/static/shared/js/lib')
    },
  resolve: {
      alias: {
          infusion: "infusion/dist/infusion-uio-no-jquery.min.js",
          figuration: "figuration/dist/js/figuration.min.js",
          "mark.js": "mark.js/dist/jquery.mark.min.js"
      }
  }
};
