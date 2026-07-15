<template>
  <section class="structure-hero" aria-hidden="true">
    <span class="node node-a"></span>
    <span class="node node-b"></span>
    <span class="node node-c"></span>
    <span class="node node-d"></span>
    <span class="line line-a"></span>
    <span class="line line-b"></span>
    <span class="line line-c"></span>
    <span class="ripple"></span>
  </section>
</template>

<style scoped lang="less">
  .structure-hero {
    position: relative;
    min-height: 160px;
    overflow: hidden;
    border: 1px solid rgba(193, 206, 220, 0.18);
    border-radius: 26px;
    background:
      radial-gradient(circle at 28% 32%, rgba(94, 133, 122, 0.08), transparent 22%),
      radial-gradient(circle at 72% 70%, rgba(165, 188, 214, 0.12), transparent 22%),
      linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(243, 248, 252, 0.94));
    box-shadow: 0 18px 42px rgba(113, 137, 165, 0.06);
  }

  .node,
  .line,
  .ripple {
    position: absolute;
  }

  .node {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #1f5c52;
    box-shadow: 0 0 0 8px rgba(31, 92, 82, 0.08);
  }

  .node-a {
    top: 30%;
    left: 18%;
  }

  .node-b {
    top: 58%;
    left: 38%;
  }

  .node-c {
    top: 38%;
    left: 64%;
  }

  .node-d {
    top: 70%;
    left: 84%;
    background: #88a7cb;
    box-shadow: 0 0 0 8px rgba(136, 167, 203, 0.12);
  }

  .line {
    height: 1px;
    transform-origin: left center;
    background: linear-gradient(90deg, rgba(31, 92, 82, 0.24), rgba(136, 167, 203, 0.3));
  }

  .line-a {
    top: 33%;
    left: 20%;
    width: 23%;
    transform: rotate(26deg);
  }

  .line-b {
    top: 57%;
    left: 40%;
    width: 24%;
    transform: rotate(-24deg);
  }

  .line-c {
    top: 41%;
    left: 66%;
    width: 18%;
    transform: rotate(34deg);
  }

  .ripple {
    top: 54%;
    left: 38%;
    width: 18px;
    height: 18px;
    margin-top: -4px;
    margin-left: -4px;
    border: 1px solid rgba(31, 92, 82, 0.2);
    border-radius: 50%;
  }
</style>
