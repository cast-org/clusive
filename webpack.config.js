var webpack = require('webpack');
const path = require('path');

module.exports = {
    mode: 'development',
    entry: {
        main: './index.js',
        internal: './shared/static/shared/js/internal.js'
    },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'shared/static/shared/js/lib')
    },
    resolve: {
        alias: {
            infusion: "infusion/dist/infusion-uio-no-jquery.min.js",
            "popper.js": "popper.js/dist/umd/popper.min.js",
            figuration: "figuration/dist/js/figuration.min.js",
            "mark.js": "mark.js/dist/jquery.mark.min.js"
        }
    }
};
