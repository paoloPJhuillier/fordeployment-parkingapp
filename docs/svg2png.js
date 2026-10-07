const sharp = require('sharp');
const fs = require('fs');
const svg = fs.readFileSync('docs/jenkins-pipeline-ea.svg');
sharp(svg, { density: 150 })
  .png()
  .toFile('docs/jenkins-pipeline-ea.png')
  .then(info => console.log('OK', info.width + 'x' + info.height))
  .catch(err => { console.error(err); process.exit(1); });
