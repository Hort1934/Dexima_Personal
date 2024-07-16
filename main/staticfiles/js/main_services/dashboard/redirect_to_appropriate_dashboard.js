if (window.innerWidth > 700 && window.location.pathname != '/dashboard/'){
    window.location = '/dashboard/';
}else if(window.innerWidth < 700 && window.location.pathname != '/mobile_dashboard/'){
    window.location = '/mobile_dashboard/';
}
