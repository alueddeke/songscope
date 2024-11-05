"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
self["webpackHotUpdate_N_E"]("app/profile/page",{

/***/ "(app-pages-browser)/./app/profile/components/Recommendations/Recommendations.tsx":
/*!********************************************************************!*\
  !*** ./app/profile/components/Recommendations/Recommendations.tsx ***!
  \********************************************************************/
/***/ (function(module, __webpack_exports__, __webpack_require__) {

eval(__webpack_require__.ts("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": function() { return /* binding */ Recommendations; }\n/* harmony export */ });\n/* harmony import */ var react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-dev-runtime */ \"(app-pages-browser)/./node_modules/next/dist/compiled/react/jsx-dev-runtime.js\");\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ \"(app-pages-browser)/./node_modules/next/dist/compiled/react/index.js\");\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var _services_axios__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../../../services/axios */ \"(app-pages-browser)/./services/axios.ts\");\n\nvar _s = $RefreshSig$();\n\n\nfunction Recommendations() {\n    _s();\n    const [recommendations, setRecommendations] = (0,react__WEBPACK_IMPORTED_MODULE_1__.useState)([]);\n    const [loading, setLoading] = (0,react__WEBPACK_IMPORTED_MODULE_1__.useState)(true);\n    const [error, setError] = (0,react__WEBPACK_IMPORTED_MODULE_1__.useState)(null);\n    (0,react__WEBPACK_IMPORTED_MODULE_1__.useEffect)(()=>{\n        const fetchRecommendations = async ()=>{\n            try {\n                const response = await (0,_services_axios__WEBPACK_IMPORTED_MODULE_2__.get)(\"/api/recommendations/\");\n                console.log(response.recommendations);\n                setRecommendations(response.recommendations);\n                setLoading(false);\n            } catch (err) {\n                console.error(err);\n                if (err instanceof Error) {\n                    setError(\"Failed to fetch recommendations: \".concat(err.message));\n                } else {\n                    setError(\"An unexpected error occurred\");\n                }\n                setLoading(false);\n            }\n        };\n        fetchRecommendations();\n    }, []);\n    if (loading) return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n        children: \"Loading recommendations...\"\n    }, void 0, false, {\n        fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n        lineNumber: 45,\n        columnNumber: 23\n    }, this);\n    if (error) return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n        children: error\n    }, void 0, false, {\n        fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n        lineNumber: 46,\n        columnNumber: 21\n    }, this);\n    return /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n        className: \"container mx-auto p-4\",\n        children: [\n            /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"h2\", {\n                className: \"text-2xl font-bold mb-4\",\n                children: \"Recommended Tracks\"\n            }, void 0, false, {\n                fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                lineNumber: 50,\n                columnNumber: 7\n            }, this),\n            /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n                className: \"grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4\",\n                children: recommendations.map((track)=>/*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n                        className: \"bg-white shadow-md rounded-lg overflow-hidden hover:shadow-lg transition-shadow duration-300\",\n                        children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n                            className: \"p-4\",\n                            children: [\n                                /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"h3\", {\n                                    className: \"font-bold text-lg truncate\",\n                                    children: track.name\n                                }, void 0, false, {\n                                    fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                    lineNumber: 58,\n                                    columnNumber: 15\n                                }, this),\n                                /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"p\", {\n                                    className: \"text-gray-600 truncate\",\n                                    children: track.artist\n                                }, void 0, false, {\n                                    fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                    lineNumber: 59,\n                                    columnNumber: 15\n                                }, this),\n                                /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"p\", {\n                                    className: \"text-gray-500 text-sm truncate\",\n                                    children: track.album\n                                }, void 0, false, {\n                                    fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                    lineNumber: 60,\n                                    columnNumber: 15\n                                }, this),\n                                track.preview_url ? /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n                                    className: \"mt-3\",\n                                    children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"audio\", {\n                                        controls: true,\n                                        className: \"w-full h-8\",\n                                        children: [\n                                            /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"source\", {\n                                                src: track.preview_url,\n                                                type: \"audio/mpeg\"\n                                            }, void 0, false, {\n                                                fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                                lineNumber: 64,\n                                                columnNumber: 21\n                                            }, this),\n                                            \"Your browser does not support the audio element.\"\n                                        ]\n                                    }, void 0, true, {\n                                        fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                        lineNumber: 63,\n                                        columnNumber: 19\n                                    }, this)\n                                }, void 0, false, {\n                                    fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                    lineNumber: 62,\n                                    columnNumber: 17\n                                }, this) : /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"div\", {\n                                    className: \"mt-3\",\n                                    children: /*#__PURE__*/ (0,react_jsx_dev_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxDEV)(\"p\", {\n                                        className: \"text-gray-500 text-sm truncate\",\n                                        children: \"Song Preview Not Available\"\n                                    }, void 0, false, {\n                                        fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                        lineNumber: 70,\n                                        columnNumber: 19\n                                    }, this)\n                                }, void 0, false, {\n                                    fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                                    lineNumber: 69,\n                                    columnNumber: 17\n                                }, this)\n                            ]\n                        }, void 0, true, {\n                            fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                            lineNumber: 57,\n                            columnNumber: 13\n                        }, this)\n                    }, track.id, false, {\n                        fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                        lineNumber: 53,\n                        columnNumber: 11\n                    }, this))\n            }, void 0, false, {\n                fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n                lineNumber: 51,\n                columnNumber: 7\n            }, this)\n        ]\n    }, void 0, true, {\n        fileName: \"/Users/antonilueddeke/Desktop/coding-projects/songscope/frontend/app/profile/components/Recommendations/Recommendations.tsx\",\n        lineNumber: 49,\n        columnNumber: 5\n    }, this);\n}\n_s(Recommendations, \"czH7UK4roy42vIF9GYrZ54ohweY=\");\n_c = Recommendations;\nvar _c;\n$RefreshReg$(_c, \"Recommendations\");\n\n\n;\n    // Wrapped in an IIFE to avoid polluting the global scope\n    ;\n    (function () {\n        var _a, _b;\n        // Legacy CSS implementations will `eval` browser code in a Node.js context\n        // to extract CSS. For backwards compatibility, we need to check we're in a\n        // browser context before continuing.\n        if (typeof self !== 'undefined' &&\n            // AMP / No-JS mode does not inject these helpers:\n            '$RefreshHelpers$' in self) {\n            // @ts-ignore __webpack_module__ is global\n            var currentExports = module.exports;\n            // @ts-ignore __webpack_module__ is global\n            var prevSignature = (_b = (_a = module.hot.data) === null || _a === void 0 ? void 0 : _a.prevSignature) !== null && _b !== void 0 ? _b : null;\n            // This cannot happen in MainTemplate because the exports mismatch between\n            // templating and execution.\n            self.$RefreshHelpers$.registerExportsForReactRefresh(currentExports, module.id);\n            // A module can be accepted automatically based on its exports, e.g. when\n            // it is a Refresh Boundary.\n            if (self.$RefreshHelpers$.isReactRefreshBoundary(currentExports)) {\n                // Save the previous exports signature on update so we can compare the boundary\n                // signatures. We avoid saving exports themselves since it causes memory leaks (https://github.com/vercel/next.js/pull/53797)\n                module.hot.dispose(function (data) {\n                    data.prevSignature =\n                        self.$RefreshHelpers$.getRefreshBoundarySignature(currentExports);\n                });\n                // Unconditionally accept an update to this module, we'll check if it's\n                // still a Refresh Boundary later.\n                // @ts-ignore importMeta is replaced in the loader\n                module.hot.accept();\n                // This field is set when the previous version of this module was a\n                // Refresh Boundary, letting us know we need to check for invalidation or\n                // enqueue an update.\n                if (prevSignature !== null) {\n                    // A boundary can become ineligible if its exports are incompatible\n                    // with the previous exports.\n                    //\n                    // For example, if you add/remove/change exports, we'll want to\n                    // re-execute the importing modules, and force those components to\n                    // re-render. Similarly, if you convert a class component to a\n                    // function, we want to invalidate the boundary.\n                    if (self.$RefreshHelpers$.shouldInvalidateReactRefreshBoundary(prevSignature, self.$RefreshHelpers$.getRefreshBoundarySignature(currentExports))) {\n                        module.hot.invalidate();\n                    }\n                    else {\n                        self.$RefreshHelpers$.scheduleUpdate();\n                    }\n                }\n            }\n            else {\n                // Since we just executed the code for the module, it's possible that the\n                // new exports made it ineligible for being a boundary.\n                // We only care about the case when we were _previously_ a boundary,\n                // because we already accepted this update (accidental side effect).\n                var isNoLongerABoundary = prevSignature !== null;\n                if (isNoLongerABoundary) {\n                    module.hot.invalidate();\n                }\n            }\n        }\n    })();\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKGFwcC1wYWdlcy1icm93c2VyKS8uL2FwcC9wcm9maWxlL2NvbXBvbmVudHMvUmVjb21tZW5kYXRpb25zL1JlY29tbWVuZGF0aW9ucy50c3giLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7OztBQUFtRDtBQUNGO0FBY2xDLFNBQVNJOztJQUN0QixNQUFNLENBQUNDLGlCQUFpQkMsbUJBQW1CLEdBQUdKLCtDQUFRQSxDQUFVLEVBQUU7SUFDbEUsTUFBTSxDQUFDSyxTQUFTQyxXQUFXLEdBQUdOLCtDQUFRQSxDQUFVO0lBQ2hELE1BQU0sQ0FBQ08sT0FBT0MsU0FBUyxHQUFHUiwrQ0FBUUEsQ0FBZ0I7SUFFbERELGdEQUFTQSxDQUFDO1FBQ1IsTUFBTVUsdUJBQXVCO1lBQzNCLElBQUk7Z0JBQ0YsTUFBTUMsV0FBVyxNQUFNVCxvREFBR0EsQ0FDeEI7Z0JBR0ZVLFFBQVFDLEdBQUcsQ0FBQ0YsU0FBU1AsZUFBZTtnQkFDcENDLG1CQUFtQk0sU0FBU1AsZUFBZTtnQkFDM0NHLFdBQVc7WUFDYixFQUFFLE9BQU9PLEtBQUs7Z0JBQ1pGLFFBQVFKLEtBQUssQ0FBQ007Z0JBQ2QsSUFBSUEsZUFBZUMsT0FBTztvQkFDeEJOLFNBQVMsb0NBQWdELE9BQVpLLElBQUlFLE9BQU87Z0JBQzFELE9BQU87b0JBQ0xQLFNBQVM7Z0JBQ1g7Z0JBQ0FGLFdBQVc7WUFDYjtRQUNGO1FBRUFHO0lBQ0YsR0FBRyxFQUFFO0lBRUwsSUFBSUosU0FBUyxxQkFBTyw4REFBQ1c7a0JBQUk7Ozs7OztJQUN6QixJQUFJVCxPQUFPLHFCQUFPLDhEQUFDUztrQkFBS1Q7Ozs7OztJQUV4QixxQkFDRSw4REFBQ1M7UUFBSUMsV0FBVTs7MEJBQ2IsOERBQUNDO2dCQUFHRCxXQUFVOzBCQUEwQjs7Ozs7OzBCQUN4Qyw4REFBQ0Q7Z0JBQUlDLFdBQVU7MEJBQ1pkLGdCQUFnQmdCLEdBQUcsQ0FBQyxDQUFDQyxzQkFDcEIsOERBQUNKO3dCQUVDQyxXQUFVO2tDQUVWLDRFQUFDRDs0QkFBSUMsV0FBVTs7OENBQ2IsOERBQUNJO29DQUFHSixXQUFVOzhDQUE4QkcsTUFBTUUsSUFBSTs7Ozs7OzhDQUN0RCw4REFBQ0M7b0NBQUVOLFdBQVU7OENBQTBCRyxNQUFNSSxNQUFNOzs7Ozs7OENBQ25ELDhEQUFDRDtvQ0FBRU4sV0FBVTs4Q0FBa0NHLE1BQU1LLEtBQUs7Ozs7OztnQ0FDekRMLE1BQU1NLFdBQVcsaUJBQ2hCLDhEQUFDVjtvQ0FBSUMsV0FBVTs4Q0FDYiw0RUFBQ1U7d0NBQU1DLFFBQVE7d0NBQUNYLFdBQVU7OzBEQUN4Qiw4REFBQ1k7Z0RBQU9DLEtBQUtWLE1BQU1NLFdBQVc7Z0RBQUVLLE1BQUs7Ozs7Ozs0Q0FBZTs7Ozs7Ozs7Ozs7eURBS3hELDhEQUFDZjtvQ0FBSUMsV0FBVTs4Q0FDYiw0RUFBQ007d0NBQUVOLFdBQVU7a0RBQWlDOzs7Ozs7Ozs7Ozs7Ozs7Ozt1QkFoQi9DRyxNQUFNWSxFQUFFOzs7Ozs7Ozs7Ozs7Ozs7O0FBMkJ6QjtHQWpFd0I5QjtLQUFBQSIsInNvdXJjZXMiOlsid2VicGFjazovL19OX0UvLi9hcHAvcHJvZmlsZS9jb21wb25lbnRzL1JlY29tbWVuZGF0aW9ucy9SZWNvbW1lbmRhdGlvbnMudHN4PzUwODgiXSwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IFJlYWN0LCB7IHVzZUVmZmVjdCwgdXNlU3RhdGUgfSBmcm9tIFwicmVhY3RcIjtcbmltcG9ydCB7IGdldCB9IGZyb20gXCIuLi8uLi8uLi8uLi9zZXJ2aWNlcy9heGlvc1wiO1xuXG5pbnRlcmZhY2UgVHJhY2sge1xuICBpZDogc3RyaW5nO1xuICBuYW1lOiBzdHJpbmc7XG4gIGFydGlzdDogc3RyaW5nO1xuICBhbGJ1bTogc3RyaW5nO1xuICBwcmV2aWV3X3VybDogc3RyaW5nIHwgbnVsbDtcbn1cblxuaW50ZXJmYWNlIFJlY29tbWVuZGF0aW9uc1Jlc3BvbnNlIHtcbiAgcmVjb21tZW5kYXRpb25zOiBUcmFja1tdO1xufVxuXG5leHBvcnQgZGVmYXVsdCBmdW5jdGlvbiBSZWNvbW1lbmRhdGlvbnMoKSB7XG4gIGNvbnN0IFtyZWNvbW1lbmRhdGlvbnMsIHNldFJlY29tbWVuZGF0aW9uc10gPSB1c2VTdGF0ZTxUcmFja1tdPihbXSk7XG4gIGNvbnN0IFtsb2FkaW5nLCBzZXRMb2FkaW5nXSA9IHVzZVN0YXRlPGJvb2xlYW4+KHRydWUpO1xuICBjb25zdCBbZXJyb3IsIHNldEVycm9yXSA9IHVzZVN0YXRlPHN0cmluZyB8IG51bGw+KG51bGwpO1xuXG4gIHVzZUVmZmVjdCgoKSA9PiB7XG4gICAgY29uc3QgZmV0Y2hSZWNvbW1lbmRhdGlvbnMgPSBhc3luYyAoKSA9PiB7XG4gICAgICB0cnkge1xuICAgICAgICBjb25zdCByZXNwb25zZSA9IGF3YWl0IGdldDxSZWNvbW1lbmRhdGlvbnNSZXNwb25zZT4oXG4gICAgICAgICAgXCIvYXBpL3JlY29tbWVuZGF0aW9ucy9cIlxuICAgICAgICApO1xuXG4gICAgICAgIGNvbnNvbGUubG9nKHJlc3BvbnNlLnJlY29tbWVuZGF0aW9ucyk7XG4gICAgICAgIHNldFJlY29tbWVuZGF0aW9ucyhyZXNwb25zZS5yZWNvbW1lbmRhdGlvbnMpO1xuICAgICAgICBzZXRMb2FkaW5nKGZhbHNlKTtcbiAgICAgIH0gY2F0Y2ggKGVycikge1xuICAgICAgICBjb25zb2xlLmVycm9yKGVycik7XG4gICAgICAgIGlmIChlcnIgaW5zdGFuY2VvZiBFcnJvcikge1xuICAgICAgICAgIHNldEVycm9yKGBGYWlsZWQgdG8gZmV0Y2ggcmVjb21tZW5kYXRpb25zOiAke2Vyci5tZXNzYWdlfWApO1xuICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgIHNldEVycm9yKFwiQW4gdW5leHBlY3RlZCBlcnJvciBvY2N1cnJlZFwiKTtcbiAgICAgICAgfVxuICAgICAgICBzZXRMb2FkaW5nKGZhbHNlKTtcbiAgICAgIH1cbiAgICB9O1xuXG4gICAgZmV0Y2hSZWNvbW1lbmRhdGlvbnMoKTtcbiAgfSwgW10pO1xuXG4gIGlmIChsb2FkaW5nKSByZXR1cm4gPGRpdj5Mb2FkaW5nIHJlY29tbWVuZGF0aW9ucy4uLjwvZGl2PjtcbiAgaWYgKGVycm9yKSByZXR1cm4gPGRpdj57ZXJyb3J9PC9kaXY+O1xuXG4gIHJldHVybiAoXG4gICAgPGRpdiBjbGFzc05hbWU9XCJjb250YWluZXIgbXgtYXV0byBwLTRcIj5cbiAgICAgIDxoMiBjbGFzc05hbWU9XCJ0ZXh0LTJ4bCBmb250LWJvbGQgbWItNFwiPlJlY29tbWVuZGVkIFRyYWNrczwvaDI+XG4gICAgICA8ZGl2IGNsYXNzTmFtZT1cImdyaWQgZ3JpZC1jb2xzLTEgbWQ6Z3JpZC1jb2xzLTIgbGc6Z3JpZC1jb2xzLTMgZ2FwLTRcIj5cbiAgICAgICAge3JlY29tbWVuZGF0aW9ucy5tYXAoKHRyYWNrKSA9PiAoXG4gICAgICAgICAgPGRpdlxuICAgICAgICAgICAga2V5PXt0cmFjay5pZH1cbiAgICAgICAgICAgIGNsYXNzTmFtZT1cImJnLXdoaXRlIHNoYWRvdy1tZCByb3VuZGVkLWxnIG92ZXJmbG93LWhpZGRlbiBob3ZlcjpzaGFkb3ctbGcgdHJhbnNpdGlvbi1zaGFkb3cgZHVyYXRpb24tMzAwXCJcbiAgICAgICAgICA+XG4gICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cInAtNFwiPlxuICAgICAgICAgICAgICA8aDMgY2xhc3NOYW1lPVwiZm9udC1ib2xkIHRleHQtbGcgdHJ1bmNhdGVcIj57dHJhY2submFtZX08L2gzPlxuICAgICAgICAgICAgICA8cCBjbGFzc05hbWU9XCJ0ZXh0LWdyYXktNjAwIHRydW5jYXRlXCI+e3RyYWNrLmFydGlzdH08L3A+XG4gICAgICAgICAgICAgIDxwIGNsYXNzTmFtZT1cInRleHQtZ3JheS01MDAgdGV4dC1zbSB0cnVuY2F0ZVwiPnt0cmFjay5hbGJ1bX08L3A+XG4gICAgICAgICAgICAgIHt0cmFjay5wcmV2aWV3X3VybCA/IChcbiAgICAgICAgICAgICAgICA8ZGl2IGNsYXNzTmFtZT1cIm10LTNcIj5cbiAgICAgICAgICAgICAgICAgIDxhdWRpbyBjb250cm9scyBjbGFzc05hbWU9XCJ3LWZ1bGwgaC04XCI+XG4gICAgICAgICAgICAgICAgICAgIDxzb3VyY2Ugc3JjPXt0cmFjay5wcmV2aWV3X3VybH0gdHlwZT1cImF1ZGlvL21wZWdcIiAvPlxuICAgICAgICAgICAgICAgICAgICBZb3VyIGJyb3dzZXIgZG9lcyBub3Qgc3VwcG9ydCB0aGUgYXVkaW8gZWxlbWVudC5cbiAgICAgICAgICAgICAgICAgIDwvYXVkaW8+XG4gICAgICAgICAgICAgICAgPC9kaXY+XG4gICAgICAgICAgICAgICkgOiAoXG4gICAgICAgICAgICAgICAgPGRpdiBjbGFzc05hbWU9XCJtdC0zXCI+XG4gICAgICAgICAgICAgICAgICA8cCBjbGFzc05hbWU9XCJ0ZXh0LWdyYXktNTAwIHRleHQtc20gdHJ1bmNhdGVcIj5cbiAgICAgICAgICAgICAgICAgICAgU29uZyBQcmV2aWV3IE5vdCBBdmFpbGFibGVcbiAgICAgICAgICAgICAgICAgIDwvcD5cbiAgICAgICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgICAgKX1cbiAgICAgICAgICAgIDwvZGl2PlxuICAgICAgICAgIDwvZGl2PlxuICAgICAgICApKX1cbiAgICAgIDwvZGl2PlxuICAgIDwvZGl2PlxuICApO1xufVxuIl0sIm5hbWVzIjpbIlJlYWN0IiwidXNlRWZmZWN0IiwidXNlU3RhdGUiLCJnZXQiLCJSZWNvbW1lbmRhdGlvbnMiLCJyZWNvbW1lbmRhdGlvbnMiLCJzZXRSZWNvbW1lbmRhdGlvbnMiLCJsb2FkaW5nIiwic2V0TG9hZGluZyIsImVycm9yIiwic2V0RXJyb3IiLCJmZXRjaFJlY29tbWVuZGF0aW9ucyIsInJlc3BvbnNlIiwiY29uc29sZSIsImxvZyIsImVyciIsIkVycm9yIiwibWVzc2FnZSIsImRpdiIsImNsYXNzTmFtZSIsImgyIiwibWFwIiwidHJhY2siLCJoMyIsIm5hbWUiLCJwIiwiYXJ0aXN0IiwiYWxidW0iLCJwcmV2aWV3X3VybCIsImF1ZGlvIiwiY29udHJvbHMiLCJzb3VyY2UiLCJzcmMiLCJ0eXBlIiwiaWQiXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///(app-pages-browser)/./app/profile/components/Recommendations/Recommendations.tsx\n"));

/***/ }),

/***/ "(app-pages-browser)/./services/axios.ts":
/*!***************************!*\
  !*** ./services/axios.ts ***!
  \***************************/
/***/ (function(module, __webpack_exports__, __webpack_require__) {

eval(__webpack_require__.ts("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   get: function() { return /* binding */ get; },\n/* harmony export */   getClient: function() { return /* binding */ getClient; }\n/* harmony export */ });\n/* harmony import */ var axios__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! axios */ \"(app-pages-browser)/./node_modules/axios/lib/axios.js\");\n\nconst BACKEND_URL = \"http://localhost:8000\" || 0;\nfunction getClient() {\n    const client = axios__WEBPACK_IMPORTED_MODULE_0__[\"default\"].create({\n        baseURL: BACKEND_URL,\n        headers: {\n            Accept: \"application/json\",\n            \"Content-Type\": \"application/json\"\n        },\n        withCredentials: true\n    });\n    return client;\n}\nasync function get(url) {\n    const client = getClient();\n    const response = await client.get(url);\n    return response.data;\n}\n\n\n;\n    // Wrapped in an IIFE to avoid polluting the global scope\n    ;\n    (function () {\n        var _a, _b;\n        // Legacy CSS implementations will `eval` browser code in a Node.js context\n        // to extract CSS. For backwards compatibility, we need to check we're in a\n        // browser context before continuing.\n        if (typeof self !== 'undefined' &&\n            // AMP / No-JS mode does not inject these helpers:\n            '$RefreshHelpers$' in self) {\n            // @ts-ignore __webpack_module__ is global\n            var currentExports = module.exports;\n            // @ts-ignore __webpack_module__ is global\n            var prevSignature = (_b = (_a = module.hot.data) === null || _a === void 0 ? void 0 : _a.prevSignature) !== null && _b !== void 0 ? _b : null;\n            // This cannot happen in MainTemplate because the exports mismatch between\n            // templating and execution.\n            self.$RefreshHelpers$.registerExportsForReactRefresh(currentExports, module.id);\n            // A module can be accepted automatically based on its exports, e.g. when\n            // it is a Refresh Boundary.\n            if (self.$RefreshHelpers$.isReactRefreshBoundary(currentExports)) {\n                // Save the previous exports signature on update so we can compare the boundary\n                // signatures. We avoid saving exports themselves since it causes memory leaks (https://github.com/vercel/next.js/pull/53797)\n                module.hot.dispose(function (data) {\n                    data.prevSignature =\n                        self.$RefreshHelpers$.getRefreshBoundarySignature(currentExports);\n                });\n                // Unconditionally accept an update to this module, we'll check if it's\n                // still a Refresh Boundary later.\n                // @ts-ignore importMeta is replaced in the loader\n                module.hot.accept();\n                // This field is set when the previous version of this module was a\n                // Refresh Boundary, letting us know we need to check for invalidation or\n                // enqueue an update.\n                if (prevSignature !== null) {\n                    // A boundary can become ineligible if its exports are incompatible\n                    // with the previous exports.\n                    //\n                    // For example, if you add/remove/change exports, we'll want to\n                    // re-execute the importing modules, and force those components to\n                    // re-render. Similarly, if you convert a class component to a\n                    // function, we want to invalidate the boundary.\n                    if (self.$RefreshHelpers$.shouldInvalidateReactRefreshBoundary(prevSignature, self.$RefreshHelpers$.getRefreshBoundarySignature(currentExports))) {\n                        module.hot.invalidate();\n                    }\n                    else {\n                        self.$RefreshHelpers$.scheduleUpdate();\n                    }\n                }\n            }\n            else {\n                // Since we just executed the code for the module, it's possible that the\n                // new exports made it ineligible for being a boundary.\n                // We only care about the case when we were _previously_ a boundary,\n                // because we already accepted this update (accidental side effect).\n                var isNoLongerABoundary = prevSignature !== null;\n                if (isNoLongerABoundary) {\n                    module.hot.invalidate();\n                }\n            }\n        }\n    })();\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKGFwcC1wYWdlcy1icm93c2VyKS8uL3NlcnZpY2VzL2F4aW9zLnRzIiwibWFwcGluZ3MiOiI7Ozs7OztBQUE2QztBQUU3QyxNQUFNQyxjQUNKQyx1QkFBbUMsSUFBSSxDQUF1QjtBQUV6RCxTQUFTRztJQUNkLE1BQU1DLFNBQVNOLDZDQUFLQSxDQUFDTyxNQUFNLENBQUM7UUFDMUJDLFNBQVNQO1FBQ1RRLFNBQVM7WUFDUEMsUUFBUTtZQUNSLGdCQUFnQjtRQUNsQjtRQUNBQyxpQkFBaUI7SUFDbkI7SUFFQSxPQUFPTDtBQUNUO0FBRU8sZUFBZU0sSUFBT0MsR0FBVztJQUN0QyxNQUFNUCxTQUFTRDtJQUNmLE1BQU1TLFdBQVcsTUFBTVIsT0FBT00sR0FBRyxDQUFJQztJQUNyQyxPQUFPQyxTQUFTQyxJQUFJO0FBQ3RCIiwic291cmNlcyI6WyJ3ZWJwYWNrOi8vX05fRS8uL3NlcnZpY2VzL2F4aW9zLnRzP2FlM2MiXSwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IGF4aW9zLCB7IEF4aW9zSW5zdGFuY2UgfSBmcm9tIFwiYXhpb3NcIjtcblxuY29uc3QgQkFDS0VORF9VUkwgPVxuICBwcm9jZXNzLmVudi5ORVhUX1BVQkxJQ19CQUNLRU5EX1VSTCB8fCBcImh0dHA6Ly9sb2NhbGhvc3Q6ODAwMFwiO1xuXG5leHBvcnQgZnVuY3Rpb24gZ2V0Q2xpZW50KCk6IEF4aW9zSW5zdGFuY2Uge1xuICBjb25zdCBjbGllbnQgPSBheGlvcy5jcmVhdGUoe1xuICAgIGJhc2VVUkw6IEJBQ0tFTkRfVVJMLFxuICAgIGhlYWRlcnM6IHtcbiAgICAgIEFjY2VwdDogXCJhcHBsaWNhdGlvbi9qc29uXCIsXG4gICAgICBcIkNvbnRlbnQtVHlwZVwiOiBcImFwcGxpY2F0aW9uL2pzb25cIixcbiAgICB9LFxuICAgIHdpdGhDcmVkZW50aWFsczogdHJ1ZSxcbiAgfSk7XG5cbiAgcmV0dXJuIGNsaWVudDtcbn1cblxuZXhwb3J0IGFzeW5jIGZ1bmN0aW9uIGdldDxUPih1cmw6IHN0cmluZyk6IFByb21pc2U8VD4ge1xuICBjb25zdCBjbGllbnQgPSBnZXRDbGllbnQoKTtcbiAgY29uc3QgcmVzcG9uc2UgPSBhd2FpdCBjbGllbnQuZ2V0PFQ+KHVybCk7XG4gIHJldHVybiByZXNwb25zZS5kYXRhO1xufVxuIl0sIm5hbWVzIjpbImF4aW9zIiwiQkFDS0VORF9VUkwiLCJwcm9jZXNzIiwiZW52IiwiTkVYVF9QVUJMSUNfQkFDS0VORF9VUkwiLCJnZXRDbGllbnQiLCJjbGllbnQiLCJjcmVhdGUiLCJiYXNlVVJMIiwiaGVhZGVycyIsIkFjY2VwdCIsIndpdGhDcmVkZW50aWFscyIsImdldCIsInVybCIsInJlc3BvbnNlIiwiZGF0YSJdLCJzb3VyY2VSb290IjoiIn0=\n//# sourceURL=webpack-internal:///(app-pages-browser)/./services/axios.ts\n"));

/***/ })

});