$(document).ready(function () {
  // 페이지 로드 시 저장된 설정 불러옴
  if (localStorage.getItem("darkMode") === "enabled") {
    $("body").addClass("dark-mode");
    updateToggleButton(true);
  }

  // 토굴 버튼 클릭 이벤트
  $(".dark-mode-toggle").on("click", function () {
    $("body").toggleClass("dark-mode");

    const isDarkMode = $("body").hasClass("dark-mode");

    // localStorage에 설정 저장
    if (isDarkMode) {
      localStorage.setItem("darkMode", "enabled");
    } else {
      localStorage.setItem("darkMode", "disabled");
    }

    // 콜백 체인: 버튼 → 모달 → 사이드바 순서로 업데이트
    updateToggleButton(isDarkMode, function () {
      console.log("1. 버튼 업데이트 완료");

      // 모달 업데이트 (콜백)
      updateModal(isDarkMode, function () {
        console.log("2. 모달 업데이트 완료");

        // 사이드바 업데이트 (콜백)
        updateSidebar(isDarkMode, function () {
          console.log("3. 사이드바 업데이트 완료");
          console.log("✅ 모든 다크모드 전환 완료!");
        });
      });
    });
  });

  // 버튼 UI 업데이트 함수
  function updateToggleButton(isDarkMode, callback) {
    $("#modeText").fadeOut(150, function () {
      if (isDarkMode) {
        $(this).text("라이트모드");
      } else {
        $(this).text("다크모드");
      }

      $(this).fadeIn(150, function () {
        if (callback) callback();
      });
    });
  }

  // 모달 업데이트 함수
  function updateModal(isDarkMode, callback) {
    $(".login-modal").fadeOut(100, function () {
      if (isDarkMode) {
        $(this).addClass("dark-mode");
      } else {
        $(this).removeClass("dark-mode");
      }

      $(this).fadeIn(100, function () {
        console.log("모달 다크모드:", isDarkMode);
        if (callback) callback();
      });
    });
  }

  // 사이드바 업데이트 함수
  function updateSidebar(isDarkMode, callback) {
    $(".sidebar").fadeOut(100, function () {
      if (isDarkMode) {
        $(this).addClass("dark-mode");
      } else {
        $(this).removeClass("dark-mode");
      }

      $(this).fadeIn(100, function () {
        console.log("사이드바 다크모드:", isDarkMode);
        if (callback) callback();
      });
    });
  }
});
