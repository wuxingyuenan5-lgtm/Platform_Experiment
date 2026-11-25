<script lang="tsx" src="./Functional.tsx"></script>
<style lang="less">
  .img-preview {
    position: fixed;
    z-index: @preview-comp-z-index;
    inset: 0;
    background: rgb(0 0 0 / 50%);
    user-select: none;

    &-content {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 100%;
      color: @white;
    }

    &-image {
      transition: transform 0.3s;
      cursor: pointer;
    }

    &__close {
      position: absolute;
      top: -40px;
      right: -40px;
      width: 80px;
      height: 80px;
      overflow: hidden;
      transition: all 0.2s;
      border-radius: 50%;
      background-color: rgb(0 0 0 / 50%);
      color: @white;
      cursor: pointer;

      &-icon {
        position: absolute;
        top: 46px;
        left: 16px;
        font-size: 16px;
      }

      &:hover {
        background-color: rgb(0 0 0 / 80%);
      }
    }

    &__index {
      position: absolute;
      bottom: 5%;
      left: 50%;
      padding: 0 22px;
      transform: translateX(-50%);
      border-radius: 15px;
      background: rgb(109 109 109 / 60%);
      font-size: 16px;
    }

    &__controller {
      display: flex;
      position: absolute;
      bottom: 10%;
      left: 50%;
      justify-content: center;
      width: 260px;
      height: 44px;
      margin-left: -139px;
      padding: 0 22px;
      border-radius: 22px;
      background: rgb(109 109 109 / 60%);

      &-item {
        display: flex;
        height: 100%;
        padding: 0 9px;
        transition: all 0.2s;
        font-size: 24px;
        cursor: pointer;

        &:hover {
          transform: scale(1.2);
        }

        img {
          width: 1em;
        }
      }
    }

    &__arrow {
      display: flex;
      position: absolute;
      top: 50%;
      align-items: center;
      justify-content: center;
      width: 50px;
      height: 50px;
      transition: all 0.2s;
      border-radius: 50%;
      background-color: rgb(0 0 0 / 50%);
      font-size: 28px;
      cursor: pointer;

      &:hover {
        background-color: rgb(0 0 0 / 80%);
      }

      &.left {
        left: 50px;
      }

      &.right {
        right: 50px;
      }
    }
  }
</style>
